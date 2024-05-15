import dataclasses

class User:
    def __init__(self, user_id, name, email, status, registration_date, premium_expiration_date, last_activity_date, notification_settings):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.status = status
        self.registration_date = registration_date
        self.premium_expiration_date = premium_expiration_date
        self.last_activity_date = last_activity_date
        self.notification_settings = notification_settings
