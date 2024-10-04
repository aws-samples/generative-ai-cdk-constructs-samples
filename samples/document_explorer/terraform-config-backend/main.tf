module "genai_doc_ingestion" {
  source  = "aws-ia/genai-document-ingestion-rag/aws"
  version = "0.0.3"
  solution_prefix    = "doc-explorer"
  container_platform = "linux/arm64"
  force_destroy      = true
}
