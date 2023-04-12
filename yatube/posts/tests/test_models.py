from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db.utils import IntegrityError

from ..models import Group, Post, Follow

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            text='Текст для поста в котором больше 15 символов.',
            author=cls.user,
        )

    def test_post_str(self):
        """Проверка __str__ у post."""
        self.assertEqual(self.post.text[:15], str(self.post))


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )

    def test_group_str(self):
        """Проверка __str__ у group."""
        self.assertEqual(self.group.title, str(self.group))


class FollowModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.author = User.objects.create_user(username='author')

    def test_constrains_for_following(self):
        """Проверка наличия ограничения на подписку на уровне БД."""
        Follow.objects.create(user=self.user, author=self.author)
        follow = Follow.objects.all().count()
        self.assertEqual(follow, 1)
        with self.assertRaises(IntegrityError):
            Follow.objects.create(user=self.user, author=self.author)
