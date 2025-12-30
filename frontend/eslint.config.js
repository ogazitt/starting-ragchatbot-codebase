import globals from 'globals';
import eslintConfigPrettier from 'eslint-config-prettier';

export default [
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        marked: 'readonly',
      },
    },
    rules: {
      // Best Practices
      eqeqeq: ['error', 'always'],
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      curly: ['error', 'all'],
      'default-case': 'warn',
      'no-fallthrough': 'error',

      // Variables
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-use-before-define': ['error', { functions: false }],
      'no-shadow': 'warn',

      // Style (non-formatting - Prettier handles formatting)
      'prefer-const': 'error',
      'no-var': 'error',
      'object-shorthand': 'warn',
      'prefer-arrow-callback': 'warn',
      'prefer-template': 'warn',

      // Possible Errors
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'warn',
      'no-alert': 'warn',
      'no-duplicate-imports': 'error',

      // ES6+
      'arrow-body-style': ['warn', 'as-needed'],
      'prefer-destructuring': [
        'warn',
        {
          array: false,
          object: true,
        },
      ],
    },
  },
  eslintConfigPrettier,
];
