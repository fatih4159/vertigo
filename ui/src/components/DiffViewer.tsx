import { useState } from 'react'
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued'
import { FileDiff } from 'lucide-react'

interface Props {
  oldCode?: string
  newCode?: string
  filename?: string
}

export default function DiffViewer({ oldCode = '', newCode = '', filename = 'diff' }: Props) {
  const [splitView, setSplitView] = useState(false)

  const styles = {
    variables: {
      dark: {
        diffViewerBackground: '#0f172a',
        diffViewerColor: '#e2e8f0',
        addedBackground: '#14532d40',
        addedColor: '#86efac',
        removedBackground: '#7f1d1d40',
        removedColor: '#fca5a5',
        wordAddedBackground: '#166534',
        wordRemovedBackground: '#991b1b',
        addedGutterBackground: '#14532d30',
        removedGutterBackground: '#7f1d1d30',
        gutterBackground: '#1e293b',
        gutterBackgroundDark: '#162032',
        highlightBackground: '#1e293b',
        highlightGutterBackground: '#263044',
        codeFoldBackground: '#1e293b',
        emptyLineBackground: '#0f172a',
        gutterColor: '#475569',
        defaultColor: '#e2e8f0',
        fullDiffViewerBackground: '#0f172a',
        diffViewerTitleBackground: '#1e293b',
        diffViewerTitleColor: '#94a3b8',
        diffViewerTitleBorderColor: '#334155',
      },
    },
  }

  return (
    <div className="flex flex-col h-full bg-bg-secondary rounded-xl border border-border overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border">
        <FileDiff className="w-4 h-4 text-accent" />
        <span className="text-sm font-medium text-slate-300 flex-1 font-mono">{filename}</span>
        <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer">
          <input
            type="checkbox"
            checked={splitView}
            onChange={(e) => setSplitView(e.target.checked)}
            className="rounded"
          />
          Split view
        </label>
      </div>

      <div className="flex-1 overflow-auto text-xs">
        <ReactDiffViewer
          oldValue={oldCode}
          newValue={newCode}
          splitView={splitView}
          compareMethod={DiffMethod.WORDS}
          useDarkTheme
          styles={styles}
          showDiffOnly
          leftTitle="Before"
          rightTitle="After"
        />
      </div>
    </div>
  )
}
