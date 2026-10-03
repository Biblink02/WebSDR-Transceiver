import ts from 'typescript'
import { resolve } from 'node:path'
import { createParsedCommandLine, createVueLanguagePlugin } from '@vue/language-core'
import { proxyCreateProgram } from '@volar/typescript/lib/node/proxyCreateProgram'

// vue-tsc's CLI patches Node's module loader, which Bun does not use. Run the
// same maintained Vue/Volar compiler APIs directly, including template checks.
// https://github.com/vuejs/language-tools/issues/6090
const configPath = resolve('tsconfig.json')
const vue = createParsedCommandLine(ts, ts.sys, configPath)
const loaded = ts.readConfigFile(configPath, ts.sys.readFile)
if (loaded.error) throw new Error(ts.flattenDiagnosticMessageText(loaded.error.messageText, '\n'))
const parsed = ts.parseJsonConfigFileContent(loaded.config, ts.sys, resolve('.'), {}, configPath,
    undefined, vue.vueOptions.extensions.map(extension => ({ extension, isMixedContent: true,
        scriptKind: ts.ScriptKind.Deferred })))
const options = { ...parsed.options, noEmit: true, allowNonTsExtensions: true }
const createProgram = proxyCreateProgram(ts, ts.createProgram, () => ({
    languagePlugins: [createVueLanguagePlugin(ts, options, vue.vueOptions, name => name)],
}))
const program = createProgram({ rootNames: parsed.fileNames, options, host: ts.createCompilerHost(options) })
const diagnostics = [...parsed.errors, ...ts.getPreEmitDiagnostics(program)]
if (diagnostics.length) {
    console.error(ts.formatDiagnosticsWithColorAndContext(diagnostics, {
        getCurrentDirectory: ts.sys.getCurrentDirectory,
        getCanonicalFileName: name => name,
        getNewLine: () => ts.sys.newLine,
    }))
    process.exit(1)
}
console.log('Vue templates and TypeScript checked successfully.')
