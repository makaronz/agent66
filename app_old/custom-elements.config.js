export default {
  globs: [
    'src/**/*.{js,ts,jsx,tsx}',
    'api/**/*.{js,ts}'
  ],
  exclude: [
    'src/**/*.test.{js,ts,jsx,tsx}',
    'src/**/*.spec.{js,ts,jsx,tsx}',
    'node_modules/**/*',
    'dist/**/*',
    'build/**/*',
    'coverage/**/*',
    'docs/**/*'
  ],
  outdir: '.',
  packagejson: true,
  dev: false,
  watch: false,
  litelement: true,
  fast: false,
  quiet: false
};