import { useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import { EditorView } from '@codemirror/view'
import { Save, RotateCcw } from 'lucide-react'

interface Props {
  value: string
  onSave: (value: string) => Promise<void>
}

const darkTheme = EditorView.theme({
  '&': {
    backgroundColor: '#1a2235',
    color: '#e2e8f0',
    fontSize: '13px',
    fontFamily: "'JetBrains Mono', monospace",
    borderRadius: '0.5rem',
    height: '100%',
  },
  '.cm-content': { padding: '12px' },
  '.cm-gutters': {
    backgroundColor: '#162032',
    color: '#475569',
    border: 'none',
    borderRadius: '0.5rem 0 0 0.5rem',
  },
  '.cm-activeLineGutter': { backgroundColor: '#1e2d45' },
  '.cm-activeLine': { backgroundColor: '#1e2d45' },
  '.cm-selectionBackground': { backgroundColor: '#4338ca50' },
  '&.cm-focused .cm-selectionBackground': { backgroundColor: '#4338ca70' },
  '.cm-cursor': { borderLeftColor: '#6366f1' },
})

export default function MasterpromptEditor({ value, onSave }: Props) {
  const [draft, setDraft] = useState(value)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isDirty = draft !== value

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await onSave(draft)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setDraft(value)
    setError(null)
  }

  return (
    <div className="flex flex-col h-full bg-bg-secondary rounded-xl border border-border overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
        <span className="text-sm font-medium text-slate-300">Masterprompt</span>
        <div className="flex items-center gap-2">
          {isDirty && (
            <span className="hidden sm:inline text-xs text-yellow-400 font-mono">unsaved</span>
          )}
          {saved && (
            <span className="text-xs text-green-400 font-mono">saved!</span>
          )}
          <button
            onClick={handleReset}
            disabled={!isDirty || saving}
            className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-bg-tertiary transition-colors disabled:opacity-40"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Reset</span>
          </button>
          <button
            onClick={handleSave}
            disabled={!isDirty || saving}
            className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg text-xs bg-accent hover:bg-accent-hover text-white transition-colors disabled:opacity-40"
          >
            <Save className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{saving ? 'Saving…' : 'Save'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-2 text-xs text-red-400 bg-red-900/20 border-b border-red-800/30">
          {error}
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        <CodeMirror
          value={draft}
          onChange={setDraft}
          height="100%"
          theme={darkTheme}
          extensions={[python()]}
          basicSetup={{
            lineNumbers: true,
            foldGutter: false,
            dropCursor: false,
            allowMultipleSelections: false,
            indentOnInput: true,
          }}
          style={{ height: '100%' }}
        />
      </div>

      {/* Footer stats */}
      <div className="px-4 py-1.5 border-t border-border text-xs text-slate-600 font-mono flex gap-4">
        <span>{draft.split('\n').length} lines</span>
        <span>{draft.length} chars</span>
        <span>~{Math.ceil(draft.length / 4)} tokens</span>
      </div>
    </div>
  )
}
