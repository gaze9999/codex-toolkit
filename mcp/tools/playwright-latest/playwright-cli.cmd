@echo off
npx.cmd --yes --prefer-online --package=@playwright/cli@latest -- playwright-cli %*
