import { useState, useCallback, useRef } from "react";

// Maximum undo history limit
const DEFAULT_MAX_UNDO_LIMIT = 10;

/**
 * useUndoRedo Hook
 *
 * A custom hook for managing undo/redo functionality with a deque-based system.
 * Supports recording actions, undoing them, and redoing them with a configurable limit.
 *
 * @param {Object} options
 * @param {number} options.maxLimit - Maximum number of actions to keep in history (default: 10)
 * @returns {Object} Undo/redo state and handlers
 */
export function useUndoRedo({ maxLimit = DEFAULT_MAX_UNDO_LIMIT } = {}) {
  // Undo/Redo Deque System
  // Deque = array where:
  // - Left side (index 0) = oldest action (trash chute)
  // - Right side (end) = newest action (active door)
  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);

  // Flag to prevent recording actions during undo/redo execution
  const isApplyingAction = useRef(false);

  /**
   * Check if we're currently applying an action (prevents recursive recording)
   */
  const isExecuting = useCallback(() => {
    return isApplyingAction.current;
  }, []);

  /**
   * Set the executing flag
   */
  const setExecuting = useCallback((value) => {
    isApplyingAction.current = value;
  }, []);

  /**
   * Add an action to the undo stack
   * Clears the redo stack (new action breaks redo timeline)
   */
  const addAction = useCallback((action) => {
    if (isApplyingAction.current) return;

    setUndoStack((prev) => {
      const newStack = [...prev, action];
      // If stack exceeds limit, remove oldest action from left
      if (newStack.length > maxLimit) {
        newStack.shift();
      }
      return newStack;
    });

    // Clear redo stack when new action is performed
    setRedoStack([]);
  }, [maxLimit]);

  /**
   * Pop the most recent action from undo stack for undoing
   * Returns the action and moves it to redo stack
   */
  const popUndo = useCallback(() => {
    if (undoStack.length === 0) return null;

    const action = undoStack[undoStack.length - 1];
    setUndoStack((prev) => prev.slice(0, -1));
    setRedoStack((prev) => [...prev, action]);

    return action;
  }, [undoStack]);

  /**
   * Pop the most recent action from redo stack for redoing
   * Returns the action and moves it to undo stack
   */
  const popRedo = useCallback(() => {
    if (redoStack.length === 0) return null;

    const action = redoStack[redoStack.length - 1];
    setRedoStack((prev) => prev.slice(0, -1));
    setUndoStack((prev) => {
      const newStack = [...prev, action];
      if (newStack.length > maxLimit) {
        newStack.shift();
      }
      return newStack;
    });

    return action;
  }, [redoStack, maxLimit]);

  /**
   * Clear both undo and redo stacks
   */
  const clearHistory = useCallback(() => {
    setUndoStack([]);
    setRedoStack([]);
  }, []);

  /**
   * Check if undo is available
   */
  const canUndo = undoStack.length > 0;

  /**
   * Check if redo is available
   */
  const canRedo = redoStack.length > 0;

  return {
    // State
    undoStack,
    redoStack,
    canUndo,
    canRedo,

    // Actions
    addAction,
    popUndo,
    popRedo,
    clearHistory,

    // Execution flag helpers
    isExecuting,
    setExecuting,
  };
}

/**
 * Action Types for workflow editor
 */
export const ActionTypes = {
  ADD_NODE: "ADD_NODE",
  REMOVE_NODE: "REMOVE_NODE",
  ADD_EDGE: "ADD_EDGE",
  REMOVE_EDGE: "REMOVE_EDGE",
  MOVE_NODE: "MOVE_NODE",
  UPDATE_PROPERTIES: "UPDATE_PROPERTIES",
};

/**
 * Create an action object for adding a node
 */
export const createAddNodeAction = (node) => ({
  type: ActionTypes.ADD_NODE,
  node: JSON.parse(JSON.stringify(node)),
});

/**
 * Create an action object for removing a node
 */
export const createRemoveNodeAction = (nodeId, node, connectedEdges = []) => ({
  type: ActionTypes.REMOVE_NODE,
  nodeId,
  node: JSON.parse(JSON.stringify(node)),
  connectedEdges: JSON.parse(JSON.stringify(connectedEdges)),
});

/**
 * Create an action object for adding an edge
 */
export const createAddEdgeAction = (edge) => ({
  type: ActionTypes.ADD_EDGE,
  edge: JSON.parse(JSON.stringify(edge)),
});

/**
 * Create an action object for removing an edge
 */
export const createRemoveEdgeAction = (edgeId, edge) => ({
  type: ActionTypes.REMOVE_EDGE,
  edgeId,
  edge: JSON.parse(JSON.stringify(edge)),
});

/**
 * Create an action object for moving a node
 */
export const createMoveNodeAction = (nodeId, oldPosition, newPosition) => ({
  type: ActionTypes.MOVE_NODE,
  nodeId,
  oldPosition: { ...oldPosition },
  newPosition: { ...newPosition },
});

/**
 * Create an action object for updating node properties
 */
export const createUpdatePropertiesAction = (nodeId, oldProperties, newProperties) => ({
  type: ActionTypes.UPDATE_PROPERTIES,
  nodeId,
  oldProperties: JSON.parse(JSON.stringify(oldProperties)),
  newProperties: JSON.parse(JSON.stringify(newProperties)),
});

export default useUndoRedo;
