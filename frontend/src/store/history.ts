/**
 * Command-pattern undo/redo store — NFR-7.2
 *
 * Usage:
 *   const { pushCommand, undo, redo, canUndo, canRedo } = useHistoryStore()
 *
 *   pushCommand({
 *     id: crypto.randomUUID(),
 *     description: 'Complete task X',
 *     execute() { ... },
 *     undo() { ... },
 *   })
 */
import { create } from 'zustand'

const MAX_HISTORY = 50

export interface Command {
  id: string
  description: string
  execute(): void
  undo(): void
}

interface HistoryState {
  undoStack: Command[]
  redoStack: Command[]
  canUndo: boolean
  canRedo: boolean
  pushCommand: (cmd: Command) => void
  undo: () => void
  redo: () => void
  clear: () => void
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  undoStack: [],
  redoStack: [],
  canUndo: false,
  canRedo: false,

  pushCommand: (cmd: Command) => {
    // Execute immediately
    cmd.execute()
    set((state) => {
      const newStack = [...state.undoStack, cmd].slice(-MAX_HISTORY)
      return {
        undoStack: newStack,
        redoStack: [],          // clear redo stack on new action
        canUndo: true,
        canRedo: false,
      }
    })
  },

  undo: () => {
    const { undoStack } = get()
    if (undoStack.length === 0) return
    const cmd = undoStack[undoStack.length - 1]
    cmd.undo()
    set((state) => {
      const newUndo = state.undoStack.slice(0, -1)
      const newRedo = [...state.redoStack, cmd]
      return {
        undoStack: newUndo,
        redoStack: newRedo,
        canUndo: newUndo.length > 0,
        canRedo: true,
      }
    })
  },

  redo: () => {
    const { redoStack } = get()
    if (redoStack.length === 0) return
    const cmd = redoStack[redoStack.length - 1]
    cmd.execute()
    set((state) => {
      const newRedo = state.redoStack.slice(0, -1)
      const newUndo = [...state.undoStack, cmd].slice(-MAX_HISTORY)
      return {
        undoStack: newUndo,
        redoStack: newRedo,
        canUndo: true,
        canRedo: newRedo.length > 0,
      }
    })
  },

  clear: () => set({ undoStack: [], redoStack: [], canUndo: false, canRedo: false }),
}))
