const path = require('node:path');

module.exports = {
  filters: {
    [path.join(__dirname, 'protected-copy.cjs')]: { texts: [] },
  },
  rules: {
    [path.join(__dirname, 'taiwan-style.cjs')]: true,
    prh: {
      rulePaths: [path.join(__dirname, 'terms.yml')],
      checkBlockQuote: false,
    },
  },
};
