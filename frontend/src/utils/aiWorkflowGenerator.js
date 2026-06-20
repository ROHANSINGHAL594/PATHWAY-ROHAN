/**
 * AI Workflow Generator API utilities
 * Handles communication with the backend AI service to generate workflows
 */

import fetchWithAuth from "./api";

/**
 * Generate a workflow flowchart from user input using AI
 * @param {Object} formData - The form data containing name, description, members, document
 * @param {Array} chatHistory - Array of chat messages with role and content
 * @returns {Promise<Object>} Object containing nodes, edges, and message
 */
export const generateWorkflowFromAI = async (formData, chatHistory = []) => {
  try {
    const response = await fetchWithAuth("/ai/generate-workflow", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: formData.name || "",
        description: formData.description || "",
        members: formData.members || "",
        document: formData.document
          ? {
              name: formData.document.name,
              type: formData.document.type,
              size: formData.document.size,
            }
          : null,
        chat_history: chatHistory,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(
        `Failed to generate workflow: ${errText || response.status}`
      );
    }

    const data = await response.json();

    // Ensure the response has the expected structure
    return {
      nodes: data.nodes || [],
      edges: data.edges || [],
      message: data.message || "Workflow generated successfully!",
    };
  } catch (error) {
    console.error("Error in generateWorkflowFromAI:", error);
    throw error;
  }
};

