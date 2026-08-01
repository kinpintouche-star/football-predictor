output "cron_log_https_url" {
  description = "HTTPS URL to read the cron log via Apache using the Elastic IP"
  value       = format("https://%s/cron-log", aws_eip.lb.public_dns)
  depends_on  = [aws_eip_association.eip_assoc]
}
