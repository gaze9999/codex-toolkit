const path = require('node:path');

// Optional personal rules layered on the Toolkit zh-TW config.
const base = path.join(__dirname, '.textlintrc.cjs');
const personal = process.env.CODEX_PROOFREADING_PERSONAL_CONFIG;

if (!personal) {
  module.exports = require(base);
} else {
  if (!path.isAbsolute(personal)) {
    throw new Error('Set CODEX_PROOFREADING_PERSONAL_CONFIG to an absolute textlint config path');
  }
  process.env.CODEX_PROOFREADING_BASE_CONFIG = base;
  module.exports = require(personal);
}
