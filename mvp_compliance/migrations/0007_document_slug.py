from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mvp_compliance', '0006_version_numbered_at_publication'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='slug',
            field=models.SlugField(
                help_text="The document's identifier in its address, such as “privacy-policy”.",
                max_length=100,
                unique=True,
                verbose_name='slug',
                default='',
            ),
            preserve_default=False,
        ),
    ]
