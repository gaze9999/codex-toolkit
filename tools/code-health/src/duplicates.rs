use crate::lexer::{keyword, Kind, Token};
use crate::{Language, Source, Span};
use serde_json::{json, Value};
use std::collections::{BTreeMap, HashMap};
use std::hash::{DefaultHasher, Hash, Hasher};

const BASE: u64 = 1_000_000_007;
const DISTANCE: u64 = 0x9e3779b97f4a7c15;
const MATCH_LIMIT: usize = 20_000;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct Window {
    file: usize,
    start: usize,
    end: usize,
}

fn identifier(token: Token<'_>, language: Language) -> bool {
    language == Language::Script && token.kind == Kind::Word && !keyword(token.text)
}

fn literal(kind: Kind) -> bool {
    matches!(
        kind,
        Kind::String | Kind::Template | Kind::Number | Kind::Regex
    )
}

fn symbol_hash(token: Token<'_>, language: Language) -> u64 {
    let mut hash = DefaultHasher::new();
    token.kind.hash(&mut hash);
    if !identifier(token, language) && !literal(token.kind) {
        token.text.hash(&mut hash);
    }
    hash.finish()
}

struct Fingerprints {
    symbols: Vec<u64>,
    previous: Vec<Option<usize>>,
    next: Vec<Option<usize>>,
}

impl Fingerprints {
    fn new(tokens: &[Token<'_>], language: Language) -> Self {
        let mut result = Self {
            symbols: Vec::with_capacity(tokens.len()),
            previous: vec![None; tokens.len()],
            next: vec![None; tokens.len()],
        };
        let mut seen = HashMap::new();
        for (index, &token) in tokens.iter().enumerate() {
            result.symbols.push(symbol_hash(token, language));
            if identifier(token, language) {
                if let Some(previous) = seen.insert(token.text, index) {
                    result.previous[index] = Some(previous);
                    result.next[previous] = Some(index);
                }
            }
        }
        result
    }

    fn symbol(&self, index: usize, start: usize) -> u64 {
        let distance = self.previous[index]
            .filter(|&previous| previous >= start)
            .map_or(0, |previous| index - previous);
        self.symbols[index].wrapping_add((distance as u64).wrapping_mul(DISTANCE))
    }

    fn slide(&self, old: u64, start: usize, end: usize, powers: &[u64]) -> u64 {
        let removed = start - 1;
        let mut hash = old
            .wrapping_sub(self.symbols[removed].wrapping_mul(powers[powers.len() - 1]))
            .wrapping_mul(BASE)
            .wrapping_add(self.symbol(end - 1, start));
        // A repeated identifier becomes a first occurrence when its previous occurrence leaves the window.
        if let Some(next) = self.next[removed].filter(|&next| next < end - 1) {
            let stale = (next - removed) as u64;
            hash = hash.wrapping_sub(
                stale
                    .wrapping_mul(DISTANCE)
                    .wrapping_mul(powers[end - 1 - next]),
            );
        }
        hash
    }
}

#[derive(Default)]
struct Renames<'a> {
    forward: HashMap<&'a str, &'a str>,
    reverse: HashMap<&'a str, &'a str>,
}

impl<'a> Renames<'a> {
    fn matches(&mut self, a: Token<'a>, b: Token<'a>, language: Language) -> bool {
        if a.kind != b.kind {
            return false;
        }
        if identifier(a, language) && identifier(b, language) {
            return *self.forward.entry(a.text).or_insert(b.text) == b.text
                && *self.reverse.entry(b.text).or_insert(a.text) == a.text;
        }
        literal(a.kind) || a.text == b.text
    }
}

fn location(source: &Source, tokens: &[Token<'_>], window: Window) -> Value {
    json!({"path":source.path,"start_line":tokens[window.start].line,"end_line":tokens[window.end - 1].end_line})
}

pub fn find(
    sources: &[Source],
    tokens: &[Vec<Token<'_>>],
    min_tokens: usize,
    retained: &[Vec<Span>],
) -> (Vec<Value>, bool) {
    let mut buckets: HashMap<u64, Vec<Window>> = HashMap::new();
    let mut runs = BTreeMap::<(usize, usize, i64), Vec<(Window, Window)>>::new();
    let mut partial = false;
    let mut found = 0;
    let mut budget = 0usize;
    let mut powers = vec![1u64; min_tokens];
    for index in 1..min_tokens {
        powers[index] = powers[index - 1].wrapping_mul(BASE);
    }
    let covered: Vec<Vec<bool>> = tokens
        .iter()
        .zip(retained)
        .map(|(file, spans)| {
            file.iter()
                .map(|token| {
                    spans
                        .iter()
                        .any(|span| span.intersects(token.line, token.end_line))
                })
                .collect()
        })
        .collect();
    'files: for (id, source) in sources.iter().enumerate() {
        let file = &tokens[id];
        if file.len() < min_tokens || covered[id].iter().all(|&skip| skip) {
            continue;
        }
        let fingerprints = Fingerprints::new(file, source.language);
        let mut rolling = (0..min_tokens).fold(0u64, |sum, index| {
            sum.wrapping_mul(BASE)
                .wrapping_add(fingerprints.symbol(index, 0))
        });
        for start in 0..=file.len() - min_tokens {
            let end = start + min_tokens;
            if start > 0 {
                rolling = fingerprints.slide(rolling, start, end, &powers);
            }
            if covered[id][start..end].contains(&true) {
                continue;
            }
            let window = Window {
                file: id,
                start,
                end,
            };
            let bucket = buckets.entry(rolling).or_default();
            for other in bucket.iter() {
                if sources[other.file].language != source.language
                    || (id == other.file && start < other.end)
                {
                    continue;
                }
                let diagonal = start as i64 - other.start as i64;
                let key = (other.file, id, diagonal);
                if runs
                    .get(&key)
                    .and_then(|row| row.last())
                    .is_some_and(|(_, right)| right.end >= end)
                {
                    continue;
                }
                budget += 1;
                if budget > 2_000_000 {
                    partial = true;
                    break 'files;
                }
                let left = &tokens[other.file];
                let mut renames = Renames::default();
                if !left[other.start..other.end]
                    .iter()
                    .zip(&file[start..end])
                    .all(|(&a, &b)| renames.matches(a, b, source.language))
                {
                    continue;
                }
                let mut a = other.end;
                let mut b = end;
                let limit = if id == other.file { start } else { left.len() };
                while a < limit
                    && b < file.len()
                    && !covered[other.file][a]
                    && !covered[id][b]
                    && renames.matches(left[a], file[b], source.language)
                {
                    a += 1;
                    b += 1;
                }
                runs.entry(key)
                    .or_default()
                    .push((Window { end: a, ..*other }, Window { end: b, ..window }));
                found += 1;
                if found >= MATCH_LIMIT {
                    partial = true;
                    break 'files;
                }
            }
            if bucket.len() < 512 {
                bucket.push(window);
            } else {
                partial = true;
            }
        }
    }
    let mut pairs = BTreeMap::<(usize, usize), Vec<(Window, Window)>>::new();
    for ((left, right, _), ranges) in runs {
        pairs.entry((left, right)).or_default().extend(ranges);
    }
    let groups = pairs.into_iter().map(|((left, right), mut ranges)| {
        ranges.sort_unstable();
        let regions = ranges.into_iter().map(|(a, b)| json!({"left":location(&sources[left], &tokens[left], a), "right":location(&sources[right], &tokens[right], b), "tokens":a.end - a.start})).collect::<Vec<_>>();
        json!({"left":sources[left].path,"right":sources[right].path,"regions":regions})
    }).collect();
    (groups, partial)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lexer::tokenize;

    #[test]
    fn rolling_hash_matches_fresh_window_after_identifiers_leave() {
        let tokens = tokenize("const a = a + b; b(a, b, a); b = b - a;", Language::Script);
        let fingerprints = Fingerprints::new(&tokens, Language::Script);
        let powers = [
            1u64,
            BASE,
            BASE.wrapping_pow(2),
            BASE.wrapping_pow(3),
            BASE.wrapping_pow(4),
        ];
        let width = powers.len();
        let fresh = |start| {
            (start..start + width).fold(0u64, |sum, index| {
                sum.wrapping_mul(BASE)
                    .wrapping_add(fingerprints.symbol(index, start))
            })
        };
        let mut rolling = fresh(0);
        for start in 1..=tokens.len() - width {
            rolling = fingerprints.slide(rolling, start, start + width, &powers);
            assert_eq!(rolling, fresh(start));
        }
    }
}
