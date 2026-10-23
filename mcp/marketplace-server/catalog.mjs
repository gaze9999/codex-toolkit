import { readFileSync } from 'node:fs';
const catalog = JSON.parse(readFileSync(new URL('./data/catalog.json', import.meta.url), 'utf8'));
const provenance = { repository: catalog.repository, revision: catalog.revision };

export function listPlugins() {
  return { ...provenance, plugins: catalog.plugins };
}
export function searchSkills(query = '', offset = 0, limit = 10) {
  if (typeof query !== 'string' || query.length > 200 || !Number.isInteger(offset) || offset < 0 ||
      !Number.isInteger(limit) || limit < 1 || limit > 30) throw new Error('Invalid search bounds');
  const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const matches = catalog.skills.filter(skill => terms.every(term =>
    (skill.id + ' ' + skill.description + ' ' + skill.plugins.join(' ')).toLowerCase().includes(term)));
  return { ...provenance, total: matches.length, skills: matches.slice(offset, offset + limit),
    nextOffset: offset + limit < matches.length ? offset + limit : null };
}
export function readSkillFile(skill, reference = 'SKILL.md', offset = 0, limit = 12000) {
  if (!catalog.skills.some(item => item.id === skill)) throw new Error('Unknown skill');
  if (typeof reference !== 'string' || reference.includes('..') || reference.includes('\\') ||
      !/^(SKILL\.md|references\/[a-zA-Z0-9_./-]+\.md)$/.test(reference)) throw new Error('Invalid reference');
  if (!Number.isInteger(offset) || offset < 0 || !Number.isInteger(limit) || limit < 1 || limit > 24000) throw new Error('Invalid read bounds');
  const path = 'skills/' + skill + '/' + reference;
  const file = catalog.files[path];
  if (!file) throw new Error('Unknown reference');
  return { ...provenance, path, url: catalog.repository + '/blob/' + catalog.revision + '/' + path,
    sha256: file.sha256, text: file.text.slice(offset, offset + limit),
    nextOffset: offset + limit < file.text.length ? offset + limit : null,
    references: Object.keys(catalog.files).filter(item => item.startsWith('skills/' + skill + '/references/')).map(item => item.slice(('skills/' + skill + '/').length)) };
}
