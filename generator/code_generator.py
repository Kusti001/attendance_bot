import random
from datetime import datetime, timedelta


class CodeGenerator:
    def __init__(self, validity_seconds=20):
        self.validity_seconds = validity_seconds
        self.current_code = None
        self.code_expires = None
        self.generate_new_code()

    def generate_new_code(self):
        """Генерирует новый случайный код"""
        self.current_code = random.randint(1000, 9999)
        self.code_expires = datetime.now() + timedelta(seconds=self.validity_seconds)
        print(f"🎯 Сгенерирован новый код: {self.current_code} (действует до {self.code_expires.strftime('%H:%M:%S')})")

    def get_current_code(self):
        """Возвращает текущий код, если он еще действителен"""
        if datetime.now() > self.code_expires:
            self.generate_new_code()
        return self.current_code

    def is_code_valid(self, code_to_check):
        """Проверяет, совпадает ли код и не истек ли срок"""
        return (code_to_check == self.current_code and datetime.now() <= self.code_expires)

    def get_time_remaining(self):
        """Возвращает оставшееся время в секундах"""
        if self.code_expires:
            remaining = (self.code_expires - datetime.now()).total_seconds()
            return max(0, int(remaining))
        return 0

