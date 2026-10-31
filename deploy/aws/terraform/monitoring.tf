# Seeing what the server does, and hearing when it breaks (D31): container
# logs in CloudWatch, and two alarms that send an email.

# Where Parley's containers send their logs. Kept 7 days, then deleted, so the
# storage stays at cents.
resource "aws_cloudwatch_log_group" "containers" {
  name              = "/parley/containers"
  retention_in_days = 7
}

# The alarm's mailbox (an SNS topic) and your email on it. AWS sends a
# "Confirm subscription" email first: click it once, or no alarm reaches you.
resource "aws_sns_topic" "alerts" {
  name = "parley-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# AWS checks the server every minute: is the machine reachable, is the
# hardware under it fine? Two failed minutes in a row: email. Also when the
# checks stop coming in at all (the server is stopped or gone). Another email
# says when it's OK again.
resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "parley-server-status-check"
  alarm_description   = "The Parley server fails its status checks, or stopped reporting."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.server.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# CPU above 80% for 15 minutes (three 5-minute averages). On a t3.small that
# also means its CPU budget is running out, and it will slow down (D30).
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "parley-server-cpu-high"
  alarm_description   = "The Parley server's CPU stayed above 80% for 15 minutes."
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.server.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
