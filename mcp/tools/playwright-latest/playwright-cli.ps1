if ($MyInvocation.ExpectingInput) {
  $input | & npx.cmd --yes --prefer-online --package=@playwright/cli@latest -- playwright-cli @args
} else {
  & npx.cmd --yes --prefer-online --package=@playwright/cli@latest -- playwright-cli @args
}
exit $LASTEXITCODE
