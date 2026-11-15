// JavaScript linter (OpenSSF warnings criterion; secure development standing rule, 15 Nov 2026).
// CI installs the pinned versions below and runs `npx eslint .`, which fails on any finding.
// eslint@9.39.5, @eslint/js@9.39.5, globals@16.5.0
import js from "@eslint/js";
import globals from "globals";

export default [
  {ignores: ["node_modules/**", "**/vendor/**", "**/*.min.js", "dist/**", "site/**"]  /* site/ is the built output, copied from site_src/ */},
  js.configs.recommended,
  {files: ["**/*.js", "**/*.cjs"], languageOptions: {ecmaVersion: 2024, sourceType: "script", globals: {...globals.browser}}},
  {files: ["**/*.mjs"], languageOptions: {ecmaVersion: 2024, sourceType: "module", globals: {...globals.node}}},
  // The integrations are Node programs (CommonJS): the command-line checker, the HTTP service and the MCP server.
  {files: ["integrations/**/*.js"], languageOptions: {sourceType: "commonjs", globals: {...globals.node}}},
  // validator.js runs in the browser and in Node (it exports itself when module exists).
  {files: ["site_src/validator.js"], languageOptions: {globals: {module: "readonly"}}},
  // Unused catch bindings are allowed; names kept on purpose start with an underscore.
  {rules: {"no-unused-vars": ["error", {varsIgnorePattern: "^_", argsIgnorePattern: "^_", caughtErrors: "none"}]}},
];
