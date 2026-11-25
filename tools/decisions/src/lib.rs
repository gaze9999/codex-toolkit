//! Validate bounded evidence and call only the official Decisions endpoint.
//! No Codex credentials or configuration are read; errors never embed input or provider text.

pub mod mcp;

use base64::Engine;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::path::Path;
use std::time::{Duration, Instant};

pub const ENDPOINT: &str = "https://api.openai.com/v1/decisions";
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
pub const MAX_BYTES: usize = 2 * 1024 * 1024;
pub const MAX_RESPONSE: usize = 2 * 1024 * 1024;
const MODEL: &str = "gpt-6-luna";

/// Safe machine-readable error code.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Problem(pub &'static str);

type Checked<T = ()> = Result<T, Problem>;

#[derive(Debug, Clone, PartialEq)]
pub struct Config {
    pub credential_env: String,
    pub model: String,
    pub timeout_seconds: f64,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            credential_env: "OPENAI_API_KEY".into(),
            model: MODEL.into(),
            timeout_seconds: 20.0,
        }
    }
}

/// Compact UTF-8 JSON as sent to the endpoint.
pub fn encode(value: &Value) -> Vec<u8> {
    serde_json::to_vec(value).unwrap_or_default()
}

pub fn read_json(path: &Path, limit: usize) -> Result<Value, ReadError> {
    use std::io::Read;
    let mut raw = Vec::new();
    std::fs::File::open(path)
        .and_then(|file| file.take(limit as u64 + 1).read_to_end(&mut raw))
        .map_err(|_| ReadError::Local)?;
    if raw.len() > limit {
        return Err(ReadError::Problem(Problem("input_too_large")));
    }
    let body = raw.strip_prefix(b"\xEF\xBB\xBF").unwrap_or(&raw);
    serde_json::from_slice(body).map_err(|_| ReadError::Problem(Problem("invalid_json")))
}

#[derive(Debug, Clone, PartialEq)]
pub enum ReadError {
    Local,
    Problem(Problem),
}

fn object(value: &Value) -> Option<&Map<String, Value>> {
    value.as_object()
}

/// Exactly the required keys plus optional ones.
fn fields(value: &Value, required: &[&str], optional: &[&str]) -> Checked {
    let map = object(value).ok_or(Problem("invalid_fields"))?;
    let complete = required.iter().all(|key| map.contains_key(*key));
    let known = map
        .keys()
        .all(|key| required.contains(&key.as_str()) || optional.contains(&key.as_str()));
    if complete && known {
        Ok(())
    } else {
        Err(Problem("invalid_fields"))
    }
}

fn text(value: &Value, limit: usize) -> Checked {
    match value.as_str() {
        Some(item) if !item.trim().is_empty() && item.chars().count() <= limit => Ok(()),
        _ => Err(Problem("invalid_text")),
    }
}

/// Integer or float, never boolean.
fn is_number(value: &Value) -> bool {
    value.is_number()
}

pub fn config_from(supplied: Option<&Value>) -> Checked<Config> {
    let mut config = Config::default();
    if let Some(value) = supplied {
        fields(value, &[], &["credential_env", "model", "timeout_seconds"])?;
        let map = object(value).ok_or(Problem("invalid_fields"))?;
        if let Some(name) = map.get("credential_env") {
            config.credential_env = name
                .as_str()
                .ok_or(Problem("invalid_credential_variable"))?
                .to_string();
        }
        if let Some(model) = map.get("model") {
            text(model, 128)?;
            config.model = model.as_str().unwrap_or_default().to_string();
        }
        if let Some(timeout) = map.get("timeout_seconds") {
            if !is_number(timeout) {
                return Err(Problem("invalid_timeout"));
            }
            config.timeout_seconds = timeout.as_f64().unwrap_or(f64::NAN);
        }
    }
    let name = config.credential_env.as_bytes();
    let valid_name = !name.is_empty()
        && name.len() <= 64
        && name[0].is_ascii_uppercase()
        && name
            .iter()
            .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || *b == b'_');
    if !valid_name {
        return Err(Problem("invalid_credential_variable"));
    }
    text(&Value::from(config.model.clone()), 128)?;
    let timeout = config.timeout_seconds;
    if !timeout.is_finite() || !(1.0..=60.0).contains(&timeout) {
        return Err(Problem("invalid_timeout"));
    }
    Ok(config)
}

fn credential(config: &Config) -> String {
    std::env::var(&config.credential_env)
        .unwrap_or_default()
        .trim()
        .to_string()
}

pub fn status(config: &Config) -> Value {
    let configured = !credential(config).is_empty();
    json!({"status": if configured { "configured" } else { "needs_credentials" },
        "credential_env": config.credential_env, "endpoint": ENDPOINT, "model": config.model,
        "credential_checked": "presence_only", "online": false, "version": VERSION})
}

fn json_data(value: &Value) -> Checked {
    let accepted = value.is_object()
        || value
            .as_array()
            .is_some_and(|items| items.iter().all(Value::is_object));
    if !accepted {
        return Err(Problem("invalid_json_evidence"));
    }
    if encode(value).len() > 262_144 {
        return Err(Problem("json_evidence_too_large"));
    }
    let mut stack = vec![(value, 1usize)];
    let mut count = 0;
    while let Some((item, depth)) = stack.pop() {
        count += 1;
        if count > 10_000 || depth > 32 {
            return Err(Problem("json_evidence_limit"));
        }
        match item {
            Value::Object(map) => stack.extend(map.values().map(|x| (x, depth + 1))),
            Value::Array(items) => stack.extend(items.iter().map(|x| (x, depth + 1))),
            _ => {}
        }
    }
    Ok(())
}

fn image(part: &Value) -> Checked {
    fields(part, &["type", "image_url"], &["detail"])?;
    let url = part["image_url"].as_str();
    let detail = part.get("detail").map_or(Some("auto"), Value::as_str);
    let (Some(url), Some(detail)) = (url, detail) else {
        return Err(Problem("invalid_image"));
    };
    if !["auto", "low", "high", "original"].contains(&detail) {
        return Err(Problem("invalid_image"));
    }
    if let Some(rest) = url.strip_prefix("data:") {
        let (kind, payload) = ["png", "jpeg", "webp"]
            .iter()
            .find_map(|kind| {
                rest.strip_prefix(&format!("image/{kind};base64,"))
                    .map(|data| (*kind, data))
            })
            .ok_or(Problem("invalid_image_data"))?;
        let alphabet = |c: char| c.is_ascii_alphanumeric() || matches!(c, '+' | '/' | '=');
        if payload.is_empty() || !payload.chars().all(alphabet) {
            return Err(Problem("invalid_image_data"));
        }
        let raw = base64::engine::general_purpose::STANDARD
            .decode(payload)
            .map_err(|_| Problem("invalid_image_data"))?;
        let valid = match kind {
            "png" => raw.starts_with(b"\x89PNG\r\n\x1a\n"),
            "jpeg" => raw.starts_with(b"\xff\xd8\xff"),
            _ => raw.starts_with(b"RIFF") && raw.get(8..12) == Some(b"WEBP"),
        };
        if !valid {
            return Err(Problem("image_signature_mismatch"));
        }
        return Ok(());
    }
    if !https_host(url) {
        return Err(Problem("invalid_image_url"));
    }
    Ok(())
}

/// HTTPS URL with a host and no credentials, split the way Python `urlsplit` does.
fn https_host(url: &str) -> bool {
    let Some((scheme, rest)) = url.split_once(':') else {
        return false;
    };
    let Some(rest) = rest.strip_prefix("//") else {
        return false;
    };
    if !scheme.eq_ignore_ascii_case("https") {
        return false;
    }
    let netloc = rest.split(['/', '?', '#']).next().unwrap_or("");
    let (userinfo, host) = match netloc.rsplit_once('@') {
        Some((userinfo, host)) => (Some(userinfo), host),
        None => (None, netloc),
    };
    if let Some(userinfo) = userinfo {
        let (user, password) = match userinfo.split_once(':') {
            Some((user, password)) => (user, Some(password)),
            None => (userinfo, None),
        };
        if !user.is_empty() || password.is_some() {
            return false;
        }
    }
    let host = if let Some(bracketed) = host.strip_prefix('[') {
        bracketed.split(']').next().unwrap_or("")
    } else {
        host.split(':').next().unwrap_or("")
    };
    !host.is_empty()
}

fn content(value: &Value, multimodal: bool) -> Checked {
    if value.is_string() {
        return text(value, 65_536);
    }
    let parts = value
        .as_array()
        .filter(|items| (1..=64).contains(&items.len()))
        .ok_or(Problem("invalid_content"))?;
    for part in parts {
        let kind = part
            .as_object()
            .and_then(|map| map.get("type"))
            .and_then(Value::as_str)
            .ok_or(Problem("invalid_content_part"))?;
        match kind {
            "input_text" => {
                fields(part, &["type", "text"], &[])?;
                text(&part["text"], 65_536)?;
            }
            "input_json" if multimodal => {
                fields(part, &["type", "data"], &[])?;
                json_data(&part["data"])?;
            }
            "input_image" if multimodal => image(part)?,
            _ => return Err(Problem("unsupported_content_part")),
        }
    }
    Ok(())
}

fn options(question: &Value, kind: &str) -> Checked {
    let (name, key, max) = if kind == "choice" {
        ("choices", "value", 255)
    } else {
        ("levels", "label", 10)
    };
    let values = question[name]
        .as_array()
        .filter(|items| (2..=max).contains(&items.len()))
        .ok_or(Problem("invalid_options"))?;
    let mut seen: Vec<&Value> = Vec::new();
    for option in values {
        fields(option, &[key], &["description"])?;
        let value = &option[key];
        let typed = if kind == "choice" {
            value.is_string() || value.is_boolean()
        } else {
            value.is_string()
        };
        if !typed {
            return Err(Problem("invalid_option"));
        }
        if value.is_string() {
            text(value, 65_536)?;
        }
        if seen.contains(&value) {
            return Err(Problem("duplicate_option"));
        }
        seen.push(value);
        if let Some(description) = option.get("description") {
            text(description, 65_536)?;
        }
    }
    Ok(())
}

/// Request merged with the configured model, ready to send.
pub fn validate(request: &Value, config: &Config) -> Checked<Value> {
    fields(request, &["input", "questions"], &["model"])?;
    let mut payload = Map::new();
    payload.insert("model".into(), config.model.clone().into());
    for (key, value) in object(request).ok_or(Problem("invalid_fields"))? {
        payload.insert(key.clone(), value.clone());
    }
    let payload = Value::Object(payload);
    if payload["model"] != MODEL {
        return Err(Problem("unsupported_model"));
    }
    if encode(&payload).len() > MAX_BYTES {
        return Err(Problem("input_too_large"));
    }
    match &payload["input"] {
        Value::String(_) => text(&payload["input"], 65_536)?,
        Value::Array(messages) if (1..=64).contains(&messages.len()) => {
            for message in messages {
                fields(message, &["role", "content"], &["type"])?;
                let role = message["role"].as_str();
                let kind = message.get("type").map_or(Some("message"), Value::as_str);
                if !matches!(role, Some("user" | "developer" | "system")) || kind != Some("message")
                {
                    return Err(Problem("unsupported_message"));
                }
                content(&message["content"], role == Some("user"))?;
            }
        }
        _ => return Err(Problem("invalid_evidence")),
    }
    let questions = payload["questions"]
        .as_array()
        .filter(|items| (1..=400).contains(&items.len()))
        .ok_or(Problem("invalid_questions"))?;
    let mut names = HashSet::new();
    for question in questions {
        if !question.is_object() {
            return Err(Problem("invalid_question"));
        }
        let kind = question["type"].as_str();
        let extra: &[&str] = match kind {
            Some("predicate") => &[],
            Some("choice") => &["choices"],
            Some("score") => &["levels"],
            _ => return Err(Problem("invalid_question_type")),
        };
        let mut required = vec!["name", "type", "instructions"];
        required.extend(extra);
        fields(question, &required, &[])?;
        text(&question["name"], 128)?;
        if !names.insert(question["name"].as_str().unwrap_or_default().to_string()) {
            return Err(Problem("duplicate_question_name"));
        }
        content(&question["instructions"], true)?;
        if let Some(kind @ ("choice" | "score")) = kind {
            options(question, kind)?;
        }
    }
    Ok(payload)
}

pub fn preview(request: &Value, config: &Config) -> Checked<Value> {
    let payload = validate(request, config)?;
    let raw = encode(&payload);
    Ok(
        json!({"status": "validated", "online": false, "bytes": raw.len(),
        "sha256": format!("{:x}", Sha256::digest(&raw)),
        "questions": payload["questions"].as_array().map_or(0, Vec::len), "model": payload["model"]}),
    )
}

fn number(value: &Value, low: f64, high: f64) -> Checked {
    match value.as_f64() {
        Some(n) if is_number(value) && n.is_finite() && n >= low && n <= high => Ok(()),
        _ => Err(Problem("invalid_response")),
    }
}

pub fn validate_response(data: &Value, payload: &Value) -> Checked {
    let bad = Problem("invalid_response");
    if !data.is_object() || !data["model"].is_string() || !data["usage"].is_object() {
        return Err(bad);
    }
    let questions = payload["questions"].as_array().ok_or(bad.clone())?;
    let answers = data["answers"]
        .as_array()
        .filter(|items| items.len() == questions.len())
        .ok_or(bad.clone())?;
    for (question, answer) in questions.iter().zip(answers) {
        if !answer.is_object() || answer["name"] != question["name"] {
            return Err(bad);
        }
        if answer["type"] == "refusal" {
            continue;
        }
        let kind = question["type"].as_str().unwrap_or_default();
        if answer["type"] != kind {
            return Err(bad);
        }
        if kind == "predicate" {
            number(&answer["probability"], 0.0, 1.0)?;
            continue;
        }
        number(&answer["confidence"], 0.0, 1.0)?;
        let (key, list) = if kind == "choice" {
            ("value", "choices")
        } else {
            ("label", "levels")
        };
        let expected: Vec<&Value> = question[list]
            .as_array()
            .into_iter()
            .flatten()
            .map(|option| &option[key])
            .collect();
        let rows = answer["probabilities"]
            .as_array()
            .filter(|rows| rows.len() == expected.len())
            .ok_or(bad.clone())?;
        let mut total = 0.0;
        let mut weighted = 0.0;
        for (index, row) in rows.iter().enumerate() {
            if !row.is_object() {
                return Err(bad);
            }
            number(&row["probability"], 0.0, 1.0)?;
            let probability = row["probability"].as_f64().unwrap_or_default();
            total += probability;
            weighted += index as f64 * probability;
            if row[key] != *expected[index] {
                return Err(bad);
            }
            if kind == "score"
                && !(row["value"].is_u64() && row["value"].as_u64() == Some(index as u64))
            {
                return Err(bad);
            }
        }
        if (total - 1.0).abs() > 0.001 {
            return Err(bad);
        }
        if kind == "choice" {
            if !expected.contains(&&answer["choice"]) {
                return Err(bad);
            }
        } else {
            number(&answer["score"], 0.0, (expected.len() - 1) as f64)?;
            if (answer["score"].as_f64().unwrap_or_default() - weighted).abs() > 0.001 {
                return Err(bad);
            }
        }
    }
    for key in ["input_tokens", "output_tokens", "total_tokens"] {
        if !data["usage"][key].is_u64() {
            return Err(bad);
        }
    }
    Ok(())
}

/// Result of one POST: HTTP status, body (at most `MAX_RESPONSE + 1` bytes) and request ID.
pub struct Reply {
    pub status: u16,
    pub body: Vec<u8>,
    pub request_id: Option<String>,
}

/// Connection, TLS or timeout failure; carries no provider text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TransportFailure;

pub trait Transport {
    /// One POST without redirects or retries.
    fn post(
        &self,
        url: &str,
        authorization: &str,
        body: Vec<u8>,
        timeout: Duration,
    ) -> Result<Reply, TransportFailure>;
}

pub struct Https;

impl Transport for Https {
    fn post(
        &self,
        url: &str,
        authorization: &str,
        body: Vec<u8>,
        timeout: Duration,
    ) -> Result<Reply, TransportFailure> {
        let agent: ureq::Agent = ureq::Agent::config_builder()
            .max_redirects(0)
            .http_status_as_error(false)
            .timeout_global(Some(timeout))
            .build()
            .into();
        let response = agent
            .post(url)
            .header("Authorization", authorization)
            .header("Content-Type", "application/json")
            .send(&body[..])
            .map_err(|_| TransportFailure)?;
        let status = response.status().as_u16();
        let request_id = response
            .headers()
            .get("x-request-id")
            .and_then(|value| value.to_str().ok())
            .map(str::to_string);
        let body = response
            .into_body()
            .into_with_config()
            .limit(MAX_RESPONSE as u64 + 1)
            .read_to_vec();
        let body = match body {
            Ok(body) => body,
            // Larger bodies stop at the limit and are reported as too large.
            Err(ureq::Error::BodyExceedsLimit(_)) => vec![0; MAX_RESPONSE + 1],
            Err(_) => return Err(TransportFailure),
        };
        Ok(Reply {
            status,
            body,
            request_id,
        })
    }
}

/// At most one request, only with explicit approval and a present credential.
pub fn evaluate(
    request: &Value,
    config: &Config,
    approved: bool,
    transport: &dyn Transport,
) -> Checked<Value> {
    let payload = validate(request, config)?;
    if !approved {
        return Ok(json!({"status": "approval_required", "online": false}));
    }
    let secret = credential(config);
    if secret.is_empty() {
        return Ok(
            json!({"status": "needs_credentials", "credential_env": config.credential_env, "online": false}),
        );
    }
    if !secret.is_ascii() || secret.chars().any(char::is_whitespace) {
        return Ok(json!({"status": "invalid_credentials", "online": false}));
    }
    let start = Instant::now();
    let timeout = Duration::from_secs_f64(config.timeout_seconds);
    let reply = transport.post(
        ENDPOINT,
        &format!("Bearer {secret}"),
        encode(&payload),
        timeout,
    );
    let mut result = match reply {
        Err(TransportFailure) => json!({"status": "transport_error"}),
        Ok(reply) if !(200..300).contains(&reply.status) => {
            json!({"status": "http_error", "http_status": reply.status})
        }
        Ok(reply) => {
            let parsed = (reply.body.len() <= MAX_RESPONSE)
                .then(|| serde_json::from_slice::<Value>(&reply.body).ok())
                .flatten()
                .filter(|data| validate_response(data, &payload).is_ok());
            match parsed {
                None => json!({"status": "invalid_response"}),
                Some(data) => {
                    let answers = data["answers"].as_array().map_or(0, Vec::len);
                    let refused = data["answers"]
                        .as_array()
                        .into_iter()
                        .flatten()
                        .filter(|answer| answer["type"] == "refusal")
                        .count();
                    let status = if refused == answers {
                        "refused"
                    } else if refused > 0 {
                        "partial_refusal"
                    } else {
                        "ok"
                    };
                    json!({"status": status, "provider": "openai", "response": data,
                        "request_id": reply.request_id})
                }
            }
        }
    };
    let map = result.as_object_mut().expect("object");
    map.insert("online".into(), true.into());
    map.insert("attempts".into(), 1.into());
    map.insert(
        "latency_ms".into(),
        (start.elapsed().as_secs_f64() * 1000.0).round().into(),
    );
    Ok(result)
}

/// Statuses that count as a completed operation for the CLI exit code.
pub fn completed(status: &str) -> bool {
    matches!(
        status,
        "configured" | "validated" | "ok" | "partial_refusal" | "refused"
    )
}

/// JSON with `", "` and `": "` separators, like Python `json.dumps`.
pub fn compact(value: &Value) -> String {
    match value {
        Value::Array(items) => format!(
            "[{}]",
            items.iter().map(compact).collect::<Vec<_>>().join(", ")
        ),
        Value::Object(fields) => format!(
            "{{{}}}",
            fields
                .iter()
                .map(|(key, item)| format!("{}: {}", Value::from(key.as_str()), compact(item)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    fn request() -> Value {
        json!({"input": "Two isolated modules have explicit owners and synthetic checks.", "questions": [
            {"name": "independent", "type": "predicate", "instructions": "Is the work independently verifiable?"}]})
    }

    struct Fake {
        reply: RefCell<Option<Result<Reply, TransportFailure>>>,
        calls: RefCell<Vec<(String, String, Vec<u8>)>>,
    }

    impl Fake {
        fn new(data: Value) -> Self {
            Self::raw(Ok(Reply {
                status: 200,
                body: serde_json::to_vec(&data).unwrap(),
                request_id: Some("synthetic".into()),
            }))
        }
        fn raw(reply: Result<Reply, TransportFailure>) -> Self {
            Self {
                reply: RefCell::new(Some(reply)),
                calls: RefCell::new(Vec::new()),
            }
        }
    }

    impl Transport for Fake {
        fn post(
            &self,
            url: &str,
            authorization: &str,
            body: Vec<u8>,
            _: Duration,
        ) -> Result<Reply, TransportFailure> {
            self.calls
                .borrow_mut()
                .push((url.into(), authorization.into(), body));
            self.reply.borrow_mut().take().unwrap()
        }
    }

    fn answer() -> Value {
        json!({"model": MODEL, "answers": [{"name": "independent", "type": "predicate", "probability": 0.7}],
            "usage": {"input_tokens": 30, "output_tokens": 0, "total_tokens": 30}})
    }

    fn with_env<T>(name: &str, value: Option<&str>, body: impl FnOnce() -> T) -> T {
        let previous = std::env::var(name).ok();
        match value {
            Some(value) => std::env::set_var(name, value),
            None => std::env::remove_var(name),
        }
        let result = body();
        match previous {
            Some(value) => std::env::set_var(name, value),
            None => std::env::remove_var(name),
        }
        result
    }

    #[test]
    fn validation_never_sends_or_echoes_evidence() {
        let result = preview(&request(), &Config::default()).unwrap();
        assert_eq!(result["status"], "validated");
        assert!(!result.to_string().contains("isolated modules"));
    }

    #[test]
    fn authority_credentials_and_one_exact_request() {
        let config = Config {
            credential_env: "DECISIONS_TEST_KEY_A".into(),
            ..Config::default()
        };
        let fake = Fake::new(answer());
        with_env("DECISIONS_TEST_KEY_A", None, || {
            assert_eq!(
                evaluate(&request(), &config, false, &fake).unwrap()["status"],
                "approval_required"
            );
            assert_eq!(
                evaluate(&request(), &config, true, &fake).unwrap()["status"],
                "needs_credentials"
            );
        });
        assert!(fake.calls.borrow().is_empty());
        let result = with_env("DECISIONS_TEST_KEY_A", Some("synthetic-secret"), || {
            evaluate(&request(), &config, true, &fake).unwrap()
        });
        assert_eq!(result["status"], "ok");
        let calls = fake.calls.borrow();
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0].0, ENDPOINT);
        assert_eq!(calls[0].1, "Bearer synthetic-secret");
        assert!(!result.to_string().contains("synthetic-secret"));
    }

    #[test]
    fn refusals_failures_and_malformed_responses_stay_distinct() {
        let config = Config {
            credential_env: "DECISIONS_TEST_KEY_B".into(),
            ..Config::default()
        };
        let mut refusal = answer();
        refusal["answers"] = json!([{"name": "independent", "type": "refusal"}]);
        let mut wrong = answer();
        wrong["answers"] =
            json!([{"name": "independent", "type": "predicate", "probability": true}]);
        let cases = vec![
            (Fake::new(refusal), "refused"),
            (Fake::new(wrong), "invalid_response"),
            (
                Fake::raw(Ok(Reply {
                    status: 401,
                    body: b"secret body".to_vec(),
                    request_id: None,
                })),
                "http_error",
            ),
            (
                Fake::raw(Ok(Reply {
                    status: 302,
                    body: Vec::new(),
                    request_id: None,
                })),
                "http_error",
            ),
            (Fake::raw(Err(TransportFailure)), "transport_error"),
            (
                Fake::raw(Ok(Reply {
                    status: 200,
                    body: vec![b' '; MAX_RESPONSE + 1],
                    request_id: None,
                })),
                "invalid_response",
            ),
        ];
        with_env("DECISIONS_TEST_KEY_B", Some("synthetic"), || {
            for (fake, expected) in cases {
                let result = evaluate(&request(), &config, true, &fake).unwrap();
                assert_eq!(result["status"], expected);
                assert!(!result.to_string().contains("secret body"));
                assert_eq!(fake.calls.borrow().len(), 1);
            }
        });
    }

    #[test]
    fn rejects_invalid_requests() {
        let mut cases = Vec::new();
        for (key, value) in [
            ("model", json!("other")),
            ("questions", json!([])),
            ("input", json!("")),
            ("input", json!("x".repeat(MAX_BYTES + 1))),
            ("extra", json!(true)),
        ] {
            let mut item = request();
            item[key] = value;
            cases.push(item);
        }
        let mut duplicate = request();
        let question = duplicate["questions"][0].clone();
        duplicate["questions"]
            .as_array_mut()
            .unwrap()
            .push(question);
        cases.push(duplicate);
        let mut bad = request();
        bad["questions"] = json!([{"type": [], "name": "bad", "instructions": "Check"}]);
        cases.push(bad);
        let mut bad = request();
        bad["input"] = json!([{"role": [], "content": "text"}]);
        cases.push(bad);
        let mut bad = request();
        bad["input"] = json!([{"role": "user", "content": [{"type": "input_image", "image_url": "https://example.com/a.png", "detail": []}]}]);
        cases.push(bad);
        for case in cases {
            assert!(validate(&case, &Config::default()).is_err(), "{case}");
        }
    }

    #[test]
    fn json_and_image_boundaries() {
        let mut item = request();
        item["input"] = json!([{"role": "user", "content": [{"type": "input_json", "data": {"temperature": 22}}]}]);
        validate(&item, &Config::default()).unwrap();
        for url in ["file:///secret.png", "data:image/png;base64,YWJj"] {
            item["input"][0]["content"] = json!([{"type": "input_image", "image_url": url}]);
            assert!(validate(&item, &Config::default()).is_err());
        }
        item["input"][0]["content"] =
            json!([{"type": "input_image", "image_url": "data:image/png;base64,iVBORw0KGgo="}]);
        validate(&item, &Config::default()).unwrap();
    }

    #[test]
    fn typed_choices_and_scores() {
        let mut item = json!({"input": "approved evidence", "questions": [{"type": "choice", "name": "route", "instructions": "Choose", "choices": [{"value": true}, {"value": "true"}]}]});
        let payload = validate(&item, &Config::default()).unwrap();
        let mut response = json!({"model": MODEL, "usage": {"input_tokens": 1, "output_tokens": 0, "total_tokens": 1},
            "answers": [{"name": "route", "type": "choice", "choice": true, "confidence": 0.8,
                "probabilities": [{"value": true, "probability": 0.8}, {"value": "true", "probability": 0.2}]}]});
        validate_response(&response, &payload).unwrap();
        response["answers"][0]["choice"] = json!(1);
        assert!(validate_response(&response, &payload).is_err());
        item["questions"] = json!([{"type": "score", "name": "fit", "instructions": "Rate", "levels": [{"label": "low"}, {"label": "high"}]}]);
        let payload = validate(&item, &Config::default()).unwrap();
        response["answers"] = json!([{"name": "fit", "type": "score", "score": 0.6, "confidence": 0.6,
            "probabilities": [{"label": "low", "value": 0, "probability": 0.4}, {"label": "high", "value": 1, "probability": 0.6}]}]);
        validate_response(&response, &payload).unwrap();
        response["answers"][0]["score"] = json!(0.4);
        assert!(validate_response(&response, &payload).is_err());
    }

    #[test]
    fn config_rules() {
        assert!(config_from(Some(&json!({"timeout_seconds": true}))).is_err());
        assert!(config_from(Some(&json!({"timeout_seconds": 61}))).is_err());
        assert!(config_from(Some(&json!({"credential_env": "lower"}))).is_err());
        assert!(config_from(Some(&json!({"api_key": "x"}))).is_err());
        let config = config_from(Some(
            &json!({"credential_env": "OPENAI_ACCESS_TOKEN", "timeout_seconds": 5}),
        ))
        .unwrap();
        assert_eq!(config.credential_env, "OPENAI_ACCESS_TOKEN");
    }
}
