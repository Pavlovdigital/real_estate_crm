from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, URL, NumberRange
from flask_wtf.file import FileField, FileRequired, FileAllowed, MultipleFileField
from app.models import User, Client, DealStatusEnum, Property # Import Property for validation if needed
import re

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', 
                           validators=[DataRequired(message="Это поле обязательно для заполнения."), 
                                       Length(min=3, max=64)]) # Adjusted min length
    email = StringField('Электронная почта', 
                        validators=[DataRequired(message="Это поле обязательно для заполнения."), 
                                    Email(message="Некорректный адрес электронной почты.")])
    password = PasswordField('Пароль', 
                             validators=[DataRequired(message="Это поле обязательно для заполнения."), 
                                         Length(min=6, message="Пароль должен содержать не менее 6 символов.")])
    confirm_password = PasswordField('Подтвердите пароль', 
                                     validators=[DataRequired(message="Это поле обязательно для заполнения."), 
                                                 EqualTo('password', message="Пароли должны совпадать.")])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято. Пожалуйста, выберите другое.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот адрес электронной почты уже зарегистрирован. Пожалуйста, используйте другой.')

class LoginForm(FlaskForm):
    email = StringField('Электронная почта', 
                        validators=[DataRequired(message="Это поле обязательно для заполнения."), 
                                    Email(message="Некорректный адрес электронной почты.")])
    password = PasswordField('Пароль', 
                             validators=[DataRequired(message="Это поле обязательно для заполнения.")])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class PropertyForm(FlaskForm):
    name = StringField('Название/Заголовок объявления', 
                       validators=[DataRequired(message="Это поле обязательно для заполнения."),
                                   Length(max=200)])
    address = StringField('Адрес (полный)', 
                          validators=[Optional(), Length(max=255)])
    
    cat = StringField("Категория недвижимости", validators=[Optional(), Length(max=32)], description="Напр: Квартира, Дом, Коммерческая")
    status = StringField("Статус объекта", validators=[Optional(), Length(max=32)], description="Напр: Активно, Продано, В архиве")

    district = StringField('Район', validators=[Optional(), Length(max=64)])
    price = FloatField('Цена (тг)', 
                       validators=[Optional(), NumberRange(min=0, message="Цена должна быть положительным числом.")])
    
    layout = StringField('Планировка', validators=[Optional(), Length(max=100)]) 
    floor = IntegerField('Этаж', validators=[Optional(), NumberRange(min=0)])
    total_floors = IntegerField('Этажей в доме', validators=[Optional(), NumberRange(min=0)])

    area = FloatField('Общая площадь (м²)', 
                      validators=[DataRequired(message="Площадь обязательна."), NumberRange(min=0, message="Площадь должна быть положительным числом.")])
    
    m = StringField("Материал стен (М)", validators=[Optional(), Length(max=32)])
    s = StringField("Площадь (S, жилая/доп.)", validators=[Optional(), Length(max=16)])
    s_kh = StringField("Площадь кухни (S_kh)", validators=[Optional(), Length(max=16)])
    blkn = StringField("Балкон/Лоджия (БЛКН)", validators=[Optional(), Length(max=16)])
    p = StringField("Расположение (P, угловая/неугловая)", validators=[Optional(), Length(max=16)])

    condition = StringField('Состояние', validators=[Optional(), Length(max=64)])
    seller_phone = StringField('Телефон продавца', validators=[Optional(), Length(max=32)])
    
    street = StringField("Улица", validators=[Optional(), Length(max=128)])
    d_kv = StringField("Дом/Квартира №", validators=[Optional(), Length(max=32)])

    year = StringField('Год постройки', validators=[Optional(), Length(max=16)]) # Was year_built
    description = TextAreaField('Описание', render_kw={"rows":4}, validators=[Optional()])
    
    source = StringField("Источник объявления", validators=[Optional(), Length(max=32)], description="Например: OLX, Krisha.kz, Вручную")
    link = StringField("Ссылка на оригинал (URL)", validators=[Optional(), URL(message="Некорректный URL."), Length(max=512)])
    external_id = StringField("Внешний ID объявления", validators=[Optional(), Length(max=128)])

    # Removed photos TextAreaField, replaced with MultipleFileField for actual uploads
    uploaded_images = MultipleFileField("Загрузить изображения (новые или для замены)", validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Разрешены только изображения (jpg, jpeg, png, gif)!')
    ])
    
    submit = SubmitField('Сохранить объект')


class ClientForm(FlaskForm):
    name = StringField('Имя клиента', 
                       validators=[DataRequired(message="Это поле обязательно для заполнения."),
                                   Length(max=120)])
    phone = StringField('Телефон', 
                        validators=[Optional(), Length(max=32)]) # Increased length
    email = StringField('Email', 
                        validators=[Optional(), Email(message="Некорректный адрес email."), 
                                    Length(max=120)])
    notes = TextAreaField('Примечания', render_kw={"rows":3})
    interests_json = TextAreaField('Интересы (JSON)', 
                                   description='Пример: {"min_price": 10000, "max_price": 50000, "districts": ["Район1", "Район2"], "min_area": 50, "condition": "Хорошее"}',
                                   render_kw={"rows":3})
    submit = SubmitField('Сохранить клиента')

    def __init__(self, *args, **kwargs): # For edit form, to pass original object for validation
        super(ClientForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj')

    def validate_phone(self, phone):
        if phone.data:
            digits = re.sub(r'\D', '', phone.data)
            if len(digits) < 5:
                raise ValidationError('Телефонный номер выглядит слишком коротким.')
            # Check for uniqueness only if phone is provided
            query = Client.query.filter_by(phone=phone.data)
            if self.obj and self.obj.id: # If editing, exclude self
                query = query.filter(Client.id != self.obj.id)
            if query.first():
                raise ValidationError('Этот телефонный номер уже используется другим клиентом.')

    def validate_email(self, email):
        if email.data: 
            query = Client.query.filter_by(email=email.data)
            if self.obj and self.obj.id: # If editing, exclude self
                query = query.filter(Client.id != self.obj.id)
            if query.first():
                raise ValidationError('Этот email уже используется другим клиентом.')


class DealForm(FlaskForm):
    title = StringField('Название сделки', 
                        validators=[DataRequired(message="Это поле обязательно для заполнения."),
                                    Length(max=150)])
    client_id = SelectField('Клиент', coerce=int, 
                            validators=[DataRequired(message="Выберите клиента.")])
    property_id = SelectField('Объект недвижимости', coerce=int, 
                              validators=[DataRequired(message="Выберите объект недвижимости.")])
    agent_id = SelectField('Агент', coerce=int, 
                           validators=[DataRequired(message="Выберите агента.")])
    stage = SelectField('Стадия сделки', choices=DealStatusEnum.choices(), # Populate choices directly
                        validators=[DataRequired(message="Выберите стадию сделки.")])
    submit = SubmitField('Сохранить сделку')


class PropertyImportForm(FlaskForm):
    excel_file = FileField("Файл Excel (.xlsx)", validators=[FileRequired(message="Выберите файл для импорта."), FileAllowed(['xlsx'], 'Только .xlsx файлы!')])
    name_col = StringField("Название объекта*", validators=[DataRequired(message="Укажите столбец для названия.")], default="Название")
    address_col = StringField("Адрес", default="Адрес")
    cat_col = StringField("Категория (КАТ)", default="Категория")
    status_col = StringField("Статус объекта", default="Статус")
    district_col = StringField("Район", default="Район")
    price_col = StringField("Цена (тг)*", validators=[DataRequired(message="Укажите столбец для цены.")], default="Цена")
    floor_col = StringField("Этаж", default="Этаж")
    total_floors_col = StringField("Этажей в доме", default="Этажей в доме")
    area_col = StringField("Общая площадь (м²)*", validators=[DataRequired(message="Укажите столбец для площади.")], default="Общая площадь")
    m_col = StringField("Материал (М)", default="Материал")
    s_col = StringField("Площадь (S, жилая/доп.)", default="Площадь жилая")
    s_kh_col = StringField("Площадь кухни (S_kh)", default="Площадь кухни")
    blkn_col = StringField("Балкон/Лоджия (БЛКН)", default="Балкон")
    p_col = StringField("Расположение (P)", default="Расположение")
    condition_col = StringField("Состояние", default="Состояние")
    seller_phone_col = StringField("Телефон продавца", default="Телефон")
    street_col = StringField("Улица", default="Улица")
    d_kv_col = StringField("Дом/Квартира №", default="Дом")
    year_col = StringField("Год постройки", default="Год постройки") 
    description_col = StringField("Описание", default="Описание")
    source_col = StringField("Источник", default="Источник")
    photos_col = StringField("Фотографии (URLы через запятую)", default="Фото") 
    link_col = StringField("Ссылка на оригинал (URL)", default="Ссылка")
    external_id_col = StringField("Внешний ID", default="ID объявления")
    submit = SubmitField("Начать импорт")

class PropertyFilterForm(FlaskForm):
    min_price = FloatField("Цена от (тг)", validators=[Optional(), NumberRange(min=0)])
    max_price = FloatField("Цена до (тг)", validators=[Optional(), NumberRange(min=0)])
    district = SelectField("Район", choices=[], validators=[Optional()])
    cat = SelectField("Категория", choices=[], validators=[Optional()]) 
    status = SelectField("Статус объекта", choices=[], validators=[Optional()])
    min_area = FloatField("Площадь от (м²)", validators=[Optional(), NumberRange(min=0)])
    max_area = FloatField("Площадь до (м²)", validators=[Optional(), NumberRange(min=0)])
    min_floor = IntegerField("Этаж от", validators=[Optional(), NumberRange(min=0)])
    max_floor = IntegerField("Этаж до", validators=[Optional(), NumberRange(min=0)])
    total_floors_min = IntegerField("Этажей в доме от", validators=[Optional(), NumberRange(min=0)])
    total_floors_max = IntegerField("Этажей в доме до", validators=[Optional(), NumberRange(min=0)])
    year_from = StringField("Год постройки от", validators=[Optional(), Length(max=4)]) 
    year_to = StringField("Год постройки до", validators=[Optional(), Length(max=4)])
    condition = SelectField("Состояние", choices=[], validators=[Optional()]) 
    layout = SelectField("Планировка", choices=[], validators=[Optional()]) 
    submit = SubmitField("Применить фильтр")

class ClientSelectionForm(FlaskForm):
    client_id = SelectField("Выберите клиента", coerce=int, 
                            validators=[DataRequired(message="Необходимо выбрать клиента.")],
                            choices=[]) 
    submit = SubmitField("Найти подходящие объекты")

class AdminUserEditForm(FlaskForm):
    username = StringField('Имя пользователя', 
                           validators=[DataRequired(message="Имя пользователя обязательно."),
                                       Length(min=3, max=64)])
    email = StringField('Email', 
                        validators=[DataRequired(message="Email обязателен."), 
                                    Email(message="Некорректный формат email."),
                                    Length(max=120)])
    role_id = SelectField('Роль', coerce=int, 
                          validators=[DataRequired(message="Необходимо выбрать роль.")],
                          choices=[]) 
    submit = SubmitField('Сохранить изменения')

    def __init__(self, *args, **kwargs): 
        super(AdminUserEditForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj')

    def validate_username(self, username_field):
        if self.obj and username_field.data != self.obj.username:
            existing_user = User.query.filter_by(username=username_field.data).first()
            if existing_user:
                raise ValidationError('Это имя пользователя уже занято другим пользователем.')

    def validate_email(self, email_field):
        if self.obj and email_field.data != self.obj.email:
            existing_user = User.query.filter_by(email=email_field.data).first()
            if existing_user:
                raise ValidationError('Этот email уже используется другим пользователем.')

class GlobalSearchForm(FlaskForm):
    query = StringField("Поиск", 
                        validators=[DataRequired(message="Введите поисковый запрос.")],
                        render_kw={"placeholder": "Поиск..."})
    # No submit button definition here if it's part of navbar HTML directly
