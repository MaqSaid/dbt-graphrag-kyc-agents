resource "aws_s3_bucket" "raw" {
  bucket = "${var.project_name}-${var.environment}-raw-data"
  tags   = { Name = "${var.project_name}-raw-data" }
}

resource "aws_s3_bucket" "audit" {
  bucket = "${var.project_name}-${var.environment}-audit-logs"
  tags   = { Name = "${var.project_name}-audit-logs" }

  lifecycle { prevent_destroy = false }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
