import { A2UIMessage } from '../types/a2ui';

export const SAMPLE_STAGE_1_A2UI: A2UIMessage[] = [
  {
    version: '0.9.1',
    createSurface: {
      surfaceId: 'main',
      catalogId: 'https://a2ui.dev/catalogs/v0.9/core',
    },
  },
  {
    version: '0.9.1',
    updateComponents: {
      surfaceId: 'main',
      components: [
        {
          id: 'root',
          component: 'Column',
          children: [
            'progress_tracker',
            'question_heading',
            'context_card_header',
            'context_card_body',
            'options_instruction',
            'opt_btn_0',
            'opt_btn_1',
            'opt_btn_2',
            'freeform_input',
            'submit_custom_btn',
          ],
        },
        {
          id: 'progress_tracker',
          component: 'Text',
          text: 'Stage 1 of 5: Core Problem & Goal',
          variant: 'caption',
        },
        {
          id: 'question_heading',
          component: 'Text',
          text: 'What specific problem does this developer tool solve, and what is the tangible outcome?',
          variant: 'h2',
        },
        {
          id: 'context_card_header',
          component: 'Text',
          text: 'Current Project Context:',
          variant: 'subtitle2',
        },
        {
          id: 'context_card_body',
          component: 'Text',
          text: 'Initial idea: A smart command-line tool for microservice deployment debugging.',
          variant: 'body2',
        },
        {
          id: 'options_instruction',
          component: 'Text',
          text: 'Select a recommended direction or provide custom input below:',
          variant: 'body1',
        },
        {
          id: 'opt_text_0',
          component: 'Text',
          text: '(Recommended) Diagnoses failing Kubernetes pod crashloops in 30 seconds from CLI',
        },
        {
          id: 'opt_btn_0',
          component: 'Button',
          child: 'opt_text_0',
          variant: 'primary',
          action: {
            event: {
              name: 'select_stage_option',
              payload: {
                stage: 'problem_and_goal',
                selected_option:
                  '(Recommended) Diagnoses failing Kubernetes pod crashloops in 30 seconds from CLI',
                option_index: 0,
              },
            },
          },
        },
        {
          id: 'opt_text_1',
          component: 'Text',
          text: 'Automatically diffs Terraform and Helm deployment drift against cluster state',
        },
        {
          id: 'opt_btn_1',
          component: 'Button',
          child: 'opt_text_1',
          variant: 'outlined',
          action: {
            event: {
              name: 'select_stage_option',
              payload: {
                stage: 'problem_and_goal',
                selected_option:
                  'Automatically diffs Terraform and Helm deployment drift against cluster state',
                option_index: 1,
              },
            },
          },
        },
        {
          id: 'opt_text_2',
          component: 'Text',
          text: 'Aggregates multi-container structured logs with AI-generated root cause diagnosis',
        },
        {
          id: 'opt_btn_2',
          component: 'Button',
          child: 'opt_text_2',
          variant: 'outlined',
          action: {
            event: {
              name: 'select_stage_option',
              payload: {
                stage: 'problem_and_goal',
                selected_option:
                  'Aggregates multi-container structured logs with AI-generated root cause diagnosis',
                option_index: 2,
              },
            },
          },
        },
        {
          id: 'freeform_input',
          component: 'TextField',
          label: 'Custom Answer / Nuance:',
          placeholder: 'Add your custom problem definition or specifics...',
          value: { path: '/ideation/problem_and_goal/custom_text' },
        },
        {
          id: 'submit_custom_text',
          component: 'Text',
          text: 'Submit & Advance to Stage 2 (Target Persona)',
        },
        {
          id: 'submit_custom_btn',
          component: 'Button',
          child: 'submit_custom_text',
          variant: 'filled',
          action: {
            event: {
              name: 'submit_stage_input',
              payload: {
                stage: 'problem_and_goal',
                action: 'advance_stage',
              },
            },
          },
        },
      ],
    },
  },
  {
    version: '0.9.1',
    updateDataModel: {
      surfaceId: 'main',
      path: '/ideation',
      value: {
        stage: 'problem_and_goal',
        stage_number: 1,
        progress: 0.2,
        available_options: [
          '(Recommended) Diagnoses failing Kubernetes pod crashloops in 30 seconds from CLI',
          'Automatically diffs Terraform and Helm deployment drift against cluster state',
          'Aggregates multi-container structured logs with AI-generated root cause diagnosis',
        ],
        problem_and_goal: {
          custom_text: '',
        },
      },
    },
  },
];

export const SAMPLE_PRD_A2UI: A2UIMessage[] = [
  {
    version: '0.9.1',
    createSurface: {
      surfaceId: 'main',
      catalogId: 'https://a2ui.dev/catalogs/v0.9/core',
    },
  },
  {
    version: '0.9.1',
    updateComponents: {
      surfaceId: 'main',
      components: [
        {
          id: 'root',
          component: 'Column',
          children: [
            'prd_header',
            'prd_instructions',
            'prd_content_view',
            'btn_export',
            'btn_revise',
          ],
        },
        {
          id: 'prd_header',
          component: 'Text',
          text: 'Stage 5 of 5: Final PRD for KubeDoctor CLI',
          variant: 'h1',
        },
        {
          id: 'prd_instructions',
          component: 'Text',
          text: 'Review your generated Product Requirements Document below. Click "Export & Save PRD.md" to generate your downloadable file.',
          variant: 'body1',
        },
        {
          id: 'prd_content_view',
          component: 'Text',
          text: `# Product Requirements Document: KubeDoctor CLI\n\n## 1. Problem Statement\nKubernetes platform engineers waste 30-45 minutes per incident deciphering CrashLoopBackOff error logs across multiple services.\n\n## 2. Target Persona\nSenior DevOps / Platform Engineer responding to on-call cluster alerts.\n\n## 3. Core MVP Scope (1-Week Build)\n- Single CLI command: \`kubedoctor debug <pod-name>\`\n- Auto-inspects events, exit codes, recent git commit SHAs, and container stderr\n- Markdown diagnosis output with recommended rollback or fix commands\n\n## 4. Non-Goals\n- No GUI dashboard or SaaS backend\n- No automatic remediation without explicit engineer confirmation`,
          variant: 'body2',
        },
        {
          id: 'btn_export_text',
          component: 'Text',
          text: '📥 Export & Save PRD.md',
        },
        {
          id: 'btn_export',
          component: 'Button',
          child: 'btn_export_text',
          variant: 'primary',
          action: {
            event: {
              name: 'export_prd_file',
              payload: {
                filename: 'PRD.md',
                action: 'download',
              },
            },
          },
        },
        {
          id: 'btn_revise_text',
          component: 'Text',
          text: '🔄 Revise Requirements',
        },
        {
          id: 'btn_revise',
          component: 'Button',
          child: 'btn_revise_text',
          variant: 'outlined',
          action: {
            event: {
              name: 'revise_stage',
              payload: {
                stage: 'problem_and_goal',
              },
            },
          },
        },
      ],
    },
  },
  {
    version: '0.9.1',
    updateDataModel: {
      surfaceId: 'main',
      path: '/ideation/prd',
      value: {
        title: 'KubeDoctor CLI',
        filename: 'PRD.md',
        ready_for_export: true,
      },
    },
  },
];
