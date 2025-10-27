from django import forms
from .models import Patient, MedicalRecord


class PatientForm(forms.ModelForm):
    """Форма для создания/редактирования пациента"""

    class Meta:
        model = Patient
        fields = [
            'last_name', 'first_name', 'middle_name',
            'birth_date', 'gender', 'address', 'phone',
            'snils', 'policy_number'
        ]
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'snils': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123-456-789 00'}),
            'policy_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class MedicalRecordForm(forms.ModelForm):
    """Форма для создания/редактирования медицинской карты"""

    class Meta:
        model = MedicalRecord
        fields = [
            'patient', 'visit_date',
            'complaints', 'anamnesis', 'anamnesis_vitae',
            'objective_status',
            'temperature', 'blood_pressure', 'pulse', 'respiratory_rate',
            'preliminary_diagnosis', 'icd10_code', 'final_diagnosis',
            'examination_plan', 'treatment_plan', 'prescriptions',
            'recommendations'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),

            # Текстовые поля
            'complaints': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'anamnesis': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'anamnesis_vitae': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'objective_status': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),

            # Витальные показатели
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '36.6'}),
            'blood_pressure': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '120/80'}),
            'pulse': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '72'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '16'}),

            # Диагноз
            'preliminary_diagnosis': forms.TextInput(attrs={'class': 'form-control'}),
            'icd10_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'J06.9'}),
            'final_diagnosis': forms.TextInput(attrs={'class': 'form-control'}),

            # Планы
            'examination_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'prescriptions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Извлекаем доктора из kwargs если передан
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.doctor:
            instance.doctor = self.doctor
        if commit:
            instance.save()
        return instance
