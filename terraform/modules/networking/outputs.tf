output "vpc_id" { value = aws_vpc.main.id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
output "public_subnet_ids" { value = aws_subnet.public[*].id }
output "ecs_security_group_id" { value = aws_security_group.ecs.id }
output "neptune_security_group_id" { value = aws_security_group.neptune.id }
output "target_group_arn" { value = aws_lb_target_group.main.arn }
output "alb_dns_name" { value = aws_lb.main.dns_name }
