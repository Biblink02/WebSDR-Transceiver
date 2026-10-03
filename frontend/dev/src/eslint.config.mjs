// @ts-check

import eslint from '@eslint/js'
import tseslint from 'typescript-eslint'
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended'
import pluginVue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import globals from 'globals'

// noinspection JSUnusedGlobalSymbols
export default [
    eslint.configs.recommended,
    ...tseslint.configs.recommended,
    ...pluginVue.configs['flat/strongly-recommended'],
    eslintPluginPrettierRecommended,
    {
        // vue and ts files
        languageOptions: {
            parser: vueParser,
            globals: {
                // Allow browser global functions
                ...globals.browser,
            },

            parserOptions: {
                parser: tseslint.parser,
                sourceType: 'module',
                extraFileExtensions: ['.vue'],
            },
        },
        rules: {
            'prettier/prettier': 'warn',
        },
    },
    {
        files: ['app/Pages/**/*.vue'],
        rules: {
            'vue/multi-word-component-names': 'off',
        },
    },
    {
        // node files
        languageOptions: {
            globals: {
                ...globals.node,
            },
        },
        files: ['vite.config.ts', 'prettier.config.mjs', 'eslint.config.mjs'],
    },
    {
        // global ignores
        ignores: ['node_modules/', 'dist/', 'public/', '**/*.pre-webassembly/', 'app/components.d.ts'],
    },
]
