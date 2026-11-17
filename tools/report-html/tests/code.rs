use report_html::code::{find, highlight, LANGS};

fn colored(text: &str, lang: &str) -> String {
    highlight(text, find(lang).unwrap())
}

fn span(kind: &str, text: &str) -> String {
    format!("<span class=\"wb-code-{kind}\">{text}</span>")
}

#[test]
fn every_language_has_a_distinct_name_and_aliases_resolve() {
    for lang in &LANGS {
        assert_eq!(find(lang.name).unwrap().name, lang.name);
    }
    assert_eq!(find("TSX").unwrap().name, "typescript");
    assert_eq!(find("yml").unwrap().name, "yaml");
    let error = find("cobol").err().unwrap();
    assert!(error.contains("typescript") && error.contains("sql"));
}

#[test]
fn typescript_tokens_and_escaping() {
    let out = colored(
        "export const n = 1.5e-3; /* a < b */ let s = `x` && null",
        "ts",
    );
    assert!(out.starts_with(&format!(
        "{} {} n = {};",
        span("keyword", "export"),
        span("keyword", "const"),
        span("number", "1.5e-3")
    )));
    assert!(
        out.contains(&span("comment", "/* a &lt; b */")) && out.contains(&span("string", "`x`"))
    );
    assert!(out.ends_with(&format!("&amp;&amp; {}", span("boolean", "null"))));
    // Words that contain a keyword, and # outside a comment, stay plain
    assert_eq!(colored("constant #x", "js"), "constant #x");
}

#[test]
fn rust_lifetimes_chars_and_nested_comments() {
    let out = colored(
        "fn f<'a>(c: char) -> &'a str { 'x' } /* a /* b */ c */ 0x1F_u8",
        "rust",
    );
    assert!(out.contains("&lt;&#39;a&gt;") && out.contains("&amp;&#39;a str"));
    assert!(out.contains(&span("string", "&#39;x&#39;")));
    assert!(
        out.contains(&span("comment", "/* a /* b */ c */"))
            && out.ends_with(&span("number", "0x1F_u8"))
    );
}

#[test]
fn python_sql_and_shell_rules() {
    let py = colored(
        "def f():\n    return None  # done\ns = '''a\n'b'\n'''",
        "py",
    );
    assert!(py.contains(&span("keyword", "def")) && py.contains(&span("boolean", "None")));
    assert!(
        py.contains(&span("comment", "# done"))
            && py.ends_with(&span(
                "string",
                "&#39;&#39;&#39;a\n&#39;b&#39;\n&#39;&#39;&#39;"
            ))
    );

    let sql = colored(
        "SELECT \"id\", [name] FROM t WHERE x = 'it''s' -- end",
        "sql",
    );
    assert!(sql.starts_with(&format!(
        "{} {}, {} {}",
        span("keyword", "SELECT"),
        span("key", "&quot;id&quot;"),
        span("key", "[name]"),
        span("keyword", "FROM")
    )));
    assert!(
        sql.contains(&span("string", "&#39;it&#39;&#39;s&#39;"))
            && sql.ends_with(&span("comment", "-- end"))
    );

    let sh = colored("if [ \"$#\" -gt 0 ]; then echo a#b; fi # tail", "bash");
    assert!(sh.contains(&span("string", "&quot;$#&quot;")) && sh.contains("echo a#b;"));
    assert!(sh.ends_with(&span("comment", "# tail")));
}

#[test]
fn data_formats_mark_keys() {
    let json = colored("{\"a\": [1, true], \"b\" : \"c\"}", "json");
    assert_eq!(
        json,
        format!(
            "{{{}: [{}, {}], {} : {}}}",
            span("key", "&quot;a&quot;"),
            span("number", "1"),
            span("boolean", "true"),
            span("key", "&quot;b&quot;"),
            span("string", "&quot;c&quot;")
        )
    );
    let yaml = colored("name: x\n- item: http://y\nflag: True # c", "yaml");
    assert!(yaml.starts_with(&span("key", "name")) && yaml.contains(&span("key", "item")));
    assert!(!yaml.contains(&span("key", "http")) && yaml.contains(&span("boolean", "True")));
    let toml = colored("[pkg]\nversion = \"1\"\n", "toml");
    assert!(
        toml.contains(&span("key", "version")) && toml.contains(&span("string", "&quot;1&quot;"))
    );
    assert_eq!(colored("a { color: #fff; }", "css"), "a { color: #fff; }");
}

#[test]
fn plain_text_unclosed_values_and_size_limit_stay_whole() {
    assert_eq!(colored("if <x>", "text"), "if &lt;x&gt;");
    assert_eq!(
        colored("s = \"open", "py"),
        format!("s = {}", span("string", "&quot;open"))
    );
    assert_eq!(colored("/* open", "ts"), span("comment", "/* open"));
    assert_eq!(
        colored("const 名稱 = '值'", "ts"),
        format!(
            "{} 名稱 = {}",
            span("keyword", "const"),
            span("string", "&#39;值&#39;")
        )
    );
    let big = "let x = 1;\n".repeat(20_000);
    assert!(!colored(&big, "ts").contains("<span"));
}
