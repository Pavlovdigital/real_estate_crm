from app import app, db
from app.models import Role

def seed_initial_roles():
    """Seeds the database with initial roles if they don't exist."""
    with app.app_context():
        default_roles = ['Admin', 'Agent', 'User']
        existing_roles = {role.name for role in Role.query.all()}
        
        roles_to_add = []
        for role_name in default_roles:
            if role_name not in existing_roles:
                roles_to_add.append(Role(name=role_name))
                print(f"Role '{role_name}' will be added.")
            else:
                print(f"Role '{role_name}' already exists.")
        
        if roles_to_add:
            db.session.add_all(roles_to_add)
            db.session.commit()
            print("Successfully added new roles to the database.")
        else:
            print("No new roles to add.")

if __name__ == '__main__':
    print("Seeding initial roles...")
    seed_initial_roles()
    print("Role seeding process complete.")
