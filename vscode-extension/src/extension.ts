import * as vscode from 'vscode';

type AgentPatch = {
  tool?: string;
  path?: string;
  diff?: string;
};

type AgentResponse = {
  route: string;
  provider: string;
  model: string;
  plan?: string[];
  tool_calls?: unknown[];
  patches?: AgentPatch[];
  answer?: string;
};

type LiveUIWorkflow = {
  label: string;
  actionKey: string;
  prompt: string;
};

function getBackendUrl(): string {
  const config = vscode.workspace.getConfiguration('autonomousSWE');
  return config.get<string>('backendUrl') || 'http://127.0.0.1:8000';
}

function getRepoPath(): string | null {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || null;
}

function getIDEContext() {
  const editor = vscode.window.activeTextEditor;
  return {
    file_path: editor?.document.uri.fsPath || null,
    language: editor?.document.languageId || null,
    selected_text: editor?.document.getText(editor.selection) || '',
    diagnostics: [] as string[],
  };
}

function normalizeUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

async function callBackend(
  message: string,
  actionKey: string | null = null
): Promise<AgentResponse> {
  const response = await fetch(`${getBackendUrl()}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      action_key: actionKey,
      repo_path: getRepoPath(),
      client: 'ide',
      ide_context: getIDEContext(),
    }),
  });

  if (!response.ok) {
    throw new Error(
      `SWE Agent request failed: ${response.status} ${await response.text()}`
    );
  }

  return (await response.json()) as AgentResponse;
}

async function callBackendWithComputerUse(
  message: string,
  actionKey: string,
  startUrl: string,
  appName: string | null,
  maxSteps: number,
  provider: 'auto' | 'openai' | 'anthropic' = 'auto',
  visionOnly = false,
  allowDestructive = false
): Promise<AgentResponse> {
  const response = await fetch(`${getBackendUrl()}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      action_key: actionKey,
      repo_path: getRepoPath(),
      client: 'ide',
      ide_context: getIDEContext(),
      computer_use: {
        start_url: startUrl,
        app_name: appName,
        max_steps: maxSteps,
        provider,
        vision_only: visionOnly,
        allow_destructive: allowDestructive,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(
      `SWE Agent request failed: ${response.status} ${await response.text()}`
    );
  }

  return (await response.json()) as AgentResponse;
}

function renderResponseToOutput(data: AgentResponse) {
  const panel = vscode.window.createOutputChannel('Autonomous SWE Agent');
  panel.clear();
  panel.appendLine(`Route: ${data.route} via ${data.provider} (${data.model})`);
  panel.appendLine('');
  panel.appendLine('Plan:');

  for (const step of data.plan || []) {
    panel.appendLine(`- ${step}`);
  }

  panel.appendLine('');
  panel.appendLine('Tool Calls:');
  panel.appendLine(JSON.stringify(data.tool_calls || [], null, 2));
  panel.appendLine('');

  if (data.patches?.length) {
    panel.appendLine('Patches:');
    for (const patch of data.patches) {
      panel.appendLine(patch.diff || '');
    }
    panel.appendLine('');
  }

  panel.appendLine('Answer:');
  panel.appendLine(data.answer || '');
  panel.show(true);
}

function buildPromptFromChatRequest(
  request: vscode.ChatRequest
): { prompt: string; actionKey: string | null } {
  const command = request.command?.trim();
  const prompt = request.prompt?.trim() || '';

  switch (command) {
    case 'architecture':
      return {
        actionKey: 'explain_architecture',
        prompt:
          prompt ||
          'Summarize the architecture of this repo and explain the main execution flow for a junior software engineer.',
      };

    case 'refactor':
      return {
        actionKey: 'refactor_plan',
        prompt:
          prompt ||
          'Create a phased refactor plan without changing behavior. Focus on module boundaries, coupling, duplication, and safest first changes.',
      };

    case 'impact':
      return {
        actionKey: 'brownfield_impact',
        prompt:
          prompt ||
          'If we change this behavior, identify which files, modules, tests, APIs, and downstream systems are most likely affected.',
      };

    case 'release':
      return {
        actionKey: 'release_readiness',
        prompt:
          prompt ||
          'Assess this repo or feature for release readiness. Cover missing tests, migration concerns, observability gaps, rollback risk, and customer impact.',
      };

    case 'incident':
      return {
        actionKey: 'incident_prevention',
        prompt:
          prompt ||
          'Identify the most likely production failure modes in this codebase or feature and recommend mitigations before release.',
      };

    case 'security':
      return {
        actionKey: 'security_review',
        prompt:
          prompt ||
          'Perform a security review of this repo. Focus on input validation, auth, secrets handling, command execution, and unsafe defaults.',
      };

    case 'performance':
      return {
        actionKey: 'performance_review',
        prompt:
          prompt ||
          'Review this codebase for performance bottlenecks and rank the top issues by likely impact.',
      };

    case 'pm':
      return {
        actionKey: 'pm_repo_analysis',
        prompt:
          prompt ||
          'Analyze this repo like a product manager. Explain what problem it solves, who the likely users are, what features exist today, the main user journeys, the biggest UX and product risks, the top missing capabilities, and a phased roadmap for what to build next.',
      };

    case 'prd':
      return {
        actionKey: 'prd_to_architecture',
        prompt:
          prompt ||
          'Turn this product requirement into architecture, domain model, APIs, testing strategy, and a phased implementation plan.',
      };

    case 'onboard':
      return {
        actionKey: 'onboarding_explainer',
        prompt:
          prompt ||
          'Explain this codebase to a new engineer. Cover what it does, where to start reading, and the main execution flow.',
      };

    case 'reverse-prd':
      return {
        actionKey: 'reverse_prd',
        prompt:
          prompt ||
          'Analyze this repo and generate a reverse PRD. Infer the product vision, target users, jobs to be done, key user journeys, implemented features, non-functional requirements, technical constraints, known gaps, risks, and a suggested roadmap. Ground the PRD in the actual codebase and clearly separate confirmed functionality from inferred intent.',
      };

    default:
      return {
        actionKey: null,
        prompt,
      };
  }
}

async function askForLiveUIWorkflow(): Promise<LiveUIWorkflow | undefined> {
  return vscode.window.showQuickPick(
    [
      {
        label: 'Reverse PRD from Live UI',
        actionKey: 'ui_reverse_prd',
        prompt: 'Inspect the running application and generate a reverse PRD grounded in the live product experience.',
      },
      {
        label: 'UI Release Auditor',
        actionKey: 'ui_release_audit',
        prompt: 'Validate the core user journeys in staging before release. Walk the key workflows, verify expected UI states, capture user-visible defects, and return a release audit grouped by severity and customer impact. Do not take destructive actions.',
      },
      {
        label: 'UI Incident Reproduction',
        actionKey: 'ui_incident_repro',
        prompt: 'Reproduce this user-reported issue in the application UI. Identify the exact failing step, capture visible evidence, and produce a triage note with suspected frontend, backend, auth, or configuration ownership.',
      },
      {
        label: 'Admin Console Verifier',
        actionKey: 'admin_console_verifier',
        prompt: 'Use the internal admin console to verify the release configuration and report mismatches with evidence.',
      },
      {
        label: 'UX and Accessibility Review',
        actionKey: 'ux_accessibility_review',
        prompt: 'Review this application as a first-time user and accessibility-conscious PM. Identify weak visual hierarchy, confusing flows, inaccessible interactions, hidden actions, and error states that may reduce task completion.',
      },
      {
        label: 'Brownfield Flow Mapper',
        actionKey: 'brownfield_flow_mapper_ui',
        prompt: 'Walk the running application and map the top navigation and user flows. Produce a brownfield flow map showing key screens, journey transitions, visible entities, and probable ownership boundaries.',
      },
      {
        label: 'Onboarding Capture from Live App',
        actionKey: 'onboarding_capture_ui',
        prompt: 'Walk the first-run or first-visit experience of the application and produce onboarding documentation with steps, screens, likely confusion points, and screenshots to include in a help guide.',
      },
      {
        label: 'Visual Regression Audit',
        actionKey: 'visual_regression_audit',
        prompt: 'Walk the top visible user journeys in the live application and identify layout breaks, hidden controls, clipped content, modal issues, and other user-visible regressions.',
      },
    ],
    { placeHolder: 'Choose a live UI workflow' }
  );
}

export function activate(context: vscode.ExtensionContext) {
  const askAgentCommand = vscode.commands.registerCommand(
    'autonomousSWE.askAgent',
    async () => {
      try {
        const prompt = await vscode.window.showInputBox({
          prompt: 'Ask the Autonomous SWE Agent',
        });

        if (!prompt) {
          return;
        }

        const data = await callBackend(prompt, null);
        renderResponseToOutput(data);
      } catch (err) {
        vscode.window.showErrorMessage(
          err instanceof Error ? err.message : String(err)
        );
      }
    }
  );

  const runLiveUICommand = vscode.commands.registerCommand(
    'autonomousSWE.runLiveUIWorkflow',
    async () => {
      try {
        const workflow = await askForLiveUIWorkflow();
        if (!workflow) return;

        const startUrlInput = await vscode.window.showInputBox({
          prompt: 'Enter the application URL',
          placeHolder: 'https://example.com',
        });
        if (!startUrlInput) return;

        const startUrl = normalizeUrl(startUrlInput);

        const appName = await vscode.window.showInputBox({
          prompt: 'App name (optional)',
          placeHolder: 'Staging App',
        });

        const maxStepsPick = await vscode.window.showQuickPick(
          ['3', '4', '5', '6', '10', '15', '20'],
          { placeHolder: 'Choose the maximum number of browser steps' }
        );
        const maxSteps = Number(maxStepsPick || '5');

        const providerPick = await vscode.window.showQuickPick(
          ['auto', 'openai', 'anthropic'],
          { placeHolder: 'Choose computer-use provider mode' }
        );
        const provider = (providerPick || 'auto') as
          | 'auto'
          | 'openai'
          | 'anthropic';

        const visionOnlyPick = await vscode.window.showQuickPick(
          ['Interactive Browser', 'Vision-first'],
          { placeHolder: 'Choose interaction mode' }
        );
        const visionOnly = visionOnlyPick === 'Vision-first';

        const allowDestructivePick = await vscode.window.showQuickPick(
          ['No', 'Yes'],
          { placeHolder: 'Allow destructive actions?' }
        );
        const allowDestructive = allowDestructivePick === 'Yes';

        const data = await callBackendWithComputerUse(
          workflow.prompt,
          workflow.actionKey,
          startUrl,
          appName || null,
          Number.isFinite(maxSteps) ? maxSteps : 5,
          provider,
          visionOnly,
          allowDestructive
        );

        renderResponseToOutput(data);
      } catch (err) {
        vscode.window.showErrorMessage(
          err instanceof Error ? err.message : String(err)
        );
      }
    }
  );

  context.subscriptions.push(askAgentCommand, runLiveUICommand);

  const handler: vscode.ChatRequestHandler = async (
    request,
    _chatContext,
    stream,
    _token
  ) => {
    try {
      const built = buildPromptFromChatRequest(request);

      if (!built.prompt) {
        stream.markdown('Please provide a prompt for the SWE agent.');
        return;
      }

      const data = await callBackend(built.prompt, built.actionKey);

      stream.markdown(
        `**Route:** ${data.route} via ${data.provider} (${data.model})`
      );

      if (data.plan?.length) {
        stream.markdown('### Plan');
        for (const step of data.plan) {
          stream.markdown(`- ${step}`);
        }
      }

      if (data.tool_calls?.length) {
        stream.markdown('### Tool Calls');
        stream.markdown('```json');
        stream.markdown(JSON.stringify(data.tool_calls, null, 2));
        stream.markdown('```');
      }

      if (data.patches?.length) {
        stream.markdown('### Patches');
        for (const patch of data.patches) {
          if (patch.path) {
            stream.markdown(`**${patch.path}**`);
          }
          stream.markdown('```diff');
          stream.markdown(patch.diff || '');
          stream.markdown('```');
        }
      }

      stream.markdown('### Answer');
      stream.markdown(data.answer || 'No answer returned.');
    } catch (err) {
      stream.markdown(
        `SWE Agent error: ${err instanceof Error ? err.message : String(err)}`
      );
    }
  };

  const participant = vscode.chat.createChatParticipant(
    'autonomousSWE.chat',
    handler
  );
  participant.iconPath = new vscode.ThemeIcon('file-code');
  context.subscriptions.push(participant);
}

export function deactivate() {}