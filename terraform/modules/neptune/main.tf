resource "aws_neptune_cluster" "main" {
  cluster_identifier = "${var.project_name}-${var.environment}"
  engine             = "neptune"
  neptune_subnet_group_name = aws_neptune_subnet_group.main.name
  vpc_security_group_ids    = [var.security_group_id]
  skip_final_snapshot       = var.environment != "prod"

  lifecycle { prevent_destroy = false }
}

resource "aws_neptune_cluster_instance" "primary" {
  cluster_identifier = aws_neptune_cluster.main.id
  instance_class     = var.instance_class
  identifier         = "${var.project_name}-${var.environment}-primary"
}

resource "aws_neptune_cluster_instance" "reader" {
  cluster_identifier = aws_neptune_cluster.main.id
  instance_class     = var.instance_class
  identifier         = "${var.project_name}-${var.environment}-reader"
}

resource "aws_neptune_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}"
  subnet_ids = var.subnet_ids
}
