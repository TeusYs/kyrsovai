
from rest_framework import serializers
from .models import (
    Applicant,
    Program,
    Achievement,
    ApplicantAchievement,
    Application,
    StrokiZayav,
)


class ApplicantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = '__all__'


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = '__all__'


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = '__all__'


class ApplicantAchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicantAchievement
        fields = '__all__'


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'


class StrokiZayavSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrokiZayav
        fields = '__all__'
