from app import app, db
from app.models import User, Role
import click # Flask's CLI is based on Click

@app.cli.command("create-admin")
@click.option('--username', required=True, help="Имя пользователя для нового администратора.")
@click.option('--email', required=True, help="Email для нового администратора.")
@click.option('--password', required=True, help="Пароль для нового администратора.") # Removed prompt, hide_input, confirmation_prompt
def create_admin_command(username, email, password):
    """Создает нового администратора (неинтерактивная версия)."""
    with app.app_context():
        # Проверка, существует ли пользователь с таким email или username
        if User.query.filter((User.username == username) | (User.email == email)).first():
            click.echo(click.style(f"Ошибка: Пользователь с именем '{username}' или email '{email}' уже существует.", fg='red'))
            return

        # Найти роль администратора
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            click.echo(click.style("Ошибка: Роль 'Admin' не найдена в базе данных. Пожалуйста, сначала создайте роль.", fg='red'))
            # Optionally, create the role if it doesn't exist
            # click.echo("Создание роли 'Admin'...")
            # admin_role = Role(name='Admin')
            # db.session.add(admin_role)
            # db.session.commit()
            # click.echo(click.style("Роль 'Admin' создана.", fg='green'))
            return 
            

        # Создать нового пользователя
        new_admin = User(username=username, email=email, role_id=admin_role.id)
        new_admin.set_password(password)
        
        db.session.add(new_admin)
        try:
            db.session.commit()
            click.echo(click.style(f"Администратор '{username}' успешно создан с email '{email}'.", fg='green'))
        except Exception as e:
            db.session.rollback()
            click.echo(click.style(f"Ошибка при создании администратора: {e}", fg='red'))

if __name__ == '__main__':
    # Note: app.run() is not called when using Flask CLI commands.
    # The FLASK_APP environment variable (set in .flaskenv) ensures 'app' is discovered.
    app.run(debug=True)
