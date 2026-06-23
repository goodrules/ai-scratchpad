-- Per-caller token usage from Vertex AI request/response logging.
--
-- PRIMARY, exact attribution. Reads the `caller` label that the demos attach to every
-- generateContent request (see models/gemini/_common.py: default_labels / labeled_config). The label
-- is stored in full_request.labels.caller, so token counts attribute to a caller WITHOUT any
-- join to the audit logs. Only rows logged AFTER labels were enabled will have a caller.
--
-- Placeholders below map to your models/gemini/.env: <PROJECT_ID> is GOOGLE_CLOUD_PROJECT, and
-- <PROJECT_ID>.<DATASET>.<LOGGING_TABLE> is BIGQUERY_LOGGING_DESTINATION (project.dataset.table).
--
-- Run (substitute your values):
--   bq query --use_legacy_sql=false --project_id=<PROJECT_ID> < models/gemini/sql/usage_by_caller.sql

SELECT
  COALESCE(JSON_VALUE(full_request, '$.labels.caller'), '(unlabeled)') AS caller,
  JSON_VALUE(full_request, '$.labels.app')                            AS app,
  model,
  COUNT(*)                                                            AS requests,
  SUM(CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount')     AS INT64)) AS prompt_tokens,
  SUM(CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64)) AS output_tokens,
  SUM(CAST(JSON_VALUE(full_response, '$.usageMetadata.totalTokenCount')      AS INT64)) AS total_tokens
FROM `<PROJECT_ID>.<DATASET>.<LOGGING_TABLE>`
WHERE logging_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY caller, app, model
ORDER BY total_tokens DESC;
