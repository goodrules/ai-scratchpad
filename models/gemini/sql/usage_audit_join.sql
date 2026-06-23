-- Per-IAM-principal token usage via a FUZZY join of request/response logging to audit logs.
--
-- SECONDARY / cross-check view. Use this for rows logged BEFORE labels existed, or to attribute
-- usage to the GCP IAM principal (principalEmail) rather than an app label.
--
-- WHY FUZZY: there is no shared key between the two tables. The audit log's `trace`/`spanId`
-- columns are NEVER populated by Vertex AI (confirmed 0/201 rows), and its requestJson/responseJson
-- are stripped to @type + model. The only overlap is (model + timestamp). We match each
-- request/response row to the nearest audit row for the same model. This is RELIABLE ONLY at
-- low / sequential volume: if two principals call the same model within the match window, the
-- attribution is ambiguous. Prefer usage_by_caller.sql (label-based, exact) when possible.
--
-- Placeholders below map to your models/gemini/.env: <PROJECT_ID> is GOOGLE_CLOUD_PROJECT, and
-- <PROJECT_ID>.<DATASET>.<LOGGING_TABLE> is BIGQUERY_LOGGING_DESTINATION (project.dataset.table).
-- The audit table lives in the same <DATASET> (the standard Cloud Audit Logs export table).
--
-- Run (substitute your values):
--   bq query --use_legacy_sql=false --project_id=<PROJECT_ID> < models/gemini/sql/usage_audit_join.sql

WITH rr AS (
  SELECT
    logging_time,
    REGEXP_EXTRACT(model, r'models/(.+)$') AS model_id,
    CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount')     AS INT64) AS prompt_tokens,
    CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64) AS output_tokens,
    CAST(JSON_VALUE(full_response, '$.usageMetadata.totalTokenCount')      AS INT64) AS total_tokens
  FROM `<PROJECT_ID>.<DATASET>.<LOGGING_TABLE>`
  WHERE logging_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
),
audit AS (
  SELECT
    timestamp,
    protopayload_auditlog.authenticationInfo.principalEmail AS principal,
    REGEXP_EXTRACT(protopayload_auditlog.resourceName, r'models/(.+)$') AS model_id
  FROM `<PROJECT_ID>.<DATASET>.cloudaudit_googleapis_com_data_access`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND protopayload_auditlog.methodName LIKE '%PredictionService.GenerateContent'
),
matched AS (
  SELECT
    rr.*,
    audit.principal,
    -- nearest audit row for the same model; the response is logged shortly AFTER the audit
    -- entry, so we expect logging_time >= audit.timestamp (small positive latency).
    ROW_NUMBER() OVER (
      PARTITION BY rr.logging_time, rr.model_id
      ORDER BY ABS(TIMESTAMP_DIFF(rr.logging_time, audit.timestamp, MILLISECOND))
    ) AS rn
  FROM rr
  JOIN audit
    ON rr.model_id = audit.model_id
   AND audit.timestamp BETWEEN TIMESTAMP_SUB(rr.logging_time, INTERVAL 30 SECOND)
                           AND TIMESTAMP_ADD(rr.logging_time, INTERVAL 5 SECOND)
)
SELECT
  principal,
  model_id,
  COUNT(*)            AS requests,
  SUM(prompt_tokens)  AS prompt_tokens,
  SUM(output_tokens)  AS output_tokens,
  SUM(total_tokens)   AS total_tokens
FROM matched
WHERE rn = 1
GROUP BY principal, model_id
ORDER BY total_tokens DESC;
