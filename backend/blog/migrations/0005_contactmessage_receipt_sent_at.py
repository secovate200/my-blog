from django.db import migrations, models


def separate_receipt_timestamp(apps, schema_editor):
    ContactMessage = apps.get_model("blog", "ContactMessage")
    ContactMessage.objects.filter(email_sent_at__isnull=False).update(
        receipt_sent_at=models.F("email_sent_at"),
        email_sent_at=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0004_contactmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="contactmessage",
            name="receipt_sent_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="접수 메일 발송일",
            ),
        ),
        migrations.RunPython(separate_receipt_timestamp, migrations.RunPython.noop),
    ]
