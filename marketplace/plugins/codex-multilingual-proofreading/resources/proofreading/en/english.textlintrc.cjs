const path = require('node:path');

module.exports = {
  filters: {
    [path.join(__dirname, '../zh-tw/protected-copy.cjs')]: { texts: [] },
  },
  rules: {
    [path.join(__dirname, '../authored-style.cjs')]: { severity: 'warning', language: 'en' },
  },
};
