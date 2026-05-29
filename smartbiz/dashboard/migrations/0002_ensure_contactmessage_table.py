from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS dashboard_contactmessage (
                id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                name varchar(150) NOT NULL,
                email varchar(254) NOT NULL,
                subject varchar(200) NOT NULL,
                message text NOT NULL,
                is_read bool NOT NULL DEFAULT 0,
                created_at datetime NOT NULL
            );
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS dashboard_contactmessage;
            """,
        ),
    ]
