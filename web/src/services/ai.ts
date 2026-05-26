import type { CodeMapNode } from '../types/codemap';

export interface AIContext {
  node: CodeMapNode;
  incoming: string[];
  outgoing: string[];
}

export interface AIEngine {
  generateExplanation(context: AIContext): Promise<string>;
}

export class MockAIProvider implements AIEngine {
  async generateExplanation(context: AIContext): Promise<string> {
    // Artificial network delay to test loading states (1.5 seconds)
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const { node, incoming, outgoing } = context;
    const isModule = !node.name;
    const name = node.name || node.id.split('.').pop() || 'Unknown';
    const complexity = node.complexity || 1;

    let response = `### Architectural Role\n\n`;
    
    if (isModule) {
      response += `The **${name}** module serves as a structural component within the system. `;
      if (incoming.length > 5) {
        response += `It is a foundational piece of the architecture, heavily relied upon by other packages. `;
      } else if (outgoing.length > 5) {
        response += `It acts as an orchestrator, pulling together various services to complete its workflows. `;
      }
    } else {
      response += `The **${name}** function is a ${node.is_async ? 'asynchronous ' : ''}routine. `;
      if (complexity > 5) {
        response += `It handles highly complex branching logic. `;
      }
    }

    response += `\n\n### Dependency Analysis\n\n`;
    if (incoming.length === 0 && outgoing.length === 0) {
      response += `This unit is entirely isolated with no direct dependencies detected in the current scope.`;
    } else {
      if (incoming.length > 0) {
        response += `- **Fan-In (${incoming.length})**: Heavily utilized by components like \`${incoming[0]}\`. Changes here have a wide blast radius.\n`;
      }
      if (outgoing.length > 0) {
        response += `- **Fan-Out (${outgoing.length})**: Depends heavily on downstream services, such as \`${outgoing[0]}\`.\n`;
      }
    }

    response += `\n\n### Maintainability & Risks\n\n`;
    if (node.isInCycle) {
      response += `**⚠️ Circular Dependency Detected:** This component participates in an architectural cycle. This drastically reduces testability and should be broken via Dependency Inversion or event-driven decoupling.\n`;
    } else if (complexity > 8 && incoming.length > 3) {
      response += `**God Object Risk:** High complexity combined with high fan-in makes this a severe bottleneck for refactoring.\n`;
    } else {
      response += `This component appears relatively stable with no critical anti-patterns detected.\n`;
    }

    response += `\n\n### Onboarding Note\n\n`;
    response += `> Start by reviewing the ${outgoing.length > 0 ? 'downstream calls' : 'internal logic'} to understand how this component fulfills its contract. Avoid modifying its signature without checking the ${incoming.length} upstream callers.`;

    return response;
  }
}

// Export a singleton instance for the app to use
export const aiService = new MockAIProvider();
