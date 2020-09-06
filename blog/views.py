from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.views.generic import ListView

from .models import Post
from .forms import EmailPostForm, CommentForm
from taggit.models import Tag
from django.db.models import Count


def post_list(request, tag_slug=None):   # tag_slug - необязательный параметр, который находиться в урле
    # Строим QuerySet из всех опубликованных постов
    object_list = Post.objects.filter(status='published')
    tag = None

    if tag_slug:
        # Получаем тэг по задданому slug
        tag = get_object_or_404(Tag, slug=tag_slug)
        # Фильтруем список постов по заданному тэгу из списка тэгов
        # (в нашем случае список содержит только один элемент, так как tag_slug - это один тэг)
        object_list = object_list.filter(tags__in=[tag])

    paginator = Paginator(object_list, 3)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(request, 'blog/post/list.html', {'posts': posts,
                                                   'tag': tag,
                                                   'page': page})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    # QuerySet (список) коментов со статусом - Active,
    # *comments* - это related name(отношение таблиц)
    object_list = post.comments.filter(active=True)
    # Пагинатор по три комента под постом
    paginator = Paginator(object_list, 3)
    # Получение параметра GET, который указывает номер текущей страницы
    page = request.GET.get('page')
    try:
        # Комент-объект с пагинацией по 3 по номеру страницы
        comments = paginator.page(page)
    except PageNotAnInteger:
        # если параметр стр не явл целым числом, извлекаем первую страницу
        comments = paginator.page(1)
    except EmptyPage:
        # если параметр явл числом превыш посл стр, то извлекаем посл стр
        comments = paginator.page(paginator.num_pages)

    new_comment = None
    # Форма добавления комента
    if request.method == 'POST':
        # Создание экземпляра формы с использование отправленных данных (POST)
        comment_form = CommentForm(data=request.POST)
        # Проверка на валидность данных в форме
        if comment_form.is_valid():
            # Создание объекта комента без записи в БД
            new_comment = comment_form.save(commit=False)
            # Присваиваем комент к выбранному посту
            new_comment.post = post
            # Запись комента в БД
            new_comment.save()
    else:
        comment_form = CommentForm()

    # value_list - возвращает кортеж со знач для заданных полей, а именно
    # список идентификаторов(id) тегов текущей записи, flat=True - преобразует в список [1,2,3...]
    post_tags_ids = post.tags.values_list('id', flat=True)
    # Мы получаем все посты по любым тегам из списка post_tags_ids, кроме текущего поста
    similar_posts = Post.objects.filter(status='published', tags__in=post_tags_ids).exclude(id=post.pk)
    # функция Count для созд вычисляемого same_tags, в котором число тегов, общих
    # со всеми запрошенными тегами
    # order_by - для сортировки same_tags по последним добавленным постам и срезаем для вывода по 4 поста
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]

    return render(request, 'blog/post/detail.html', {'post': post,
                                                     'comments': comments,
                                                     'comment_form': comment_form,
                                                     'new_comment': new_comment,
                                                     'page': page,
                                                     'similar_posts': similar_posts,
                                                     'object_list': object_list})


def post_share(request, post_id):
    # Извлекаем пост по ID и выполняем проверку, что пост опубликован
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    cd = None
    # Условие различения двух сценариев GET и POST
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # cleaned_data - словарь полей форм и их значения
            cd = form.cleaned_data
            # get_absolut_url - извлекает абсолютный путь к посту(ссылка к конкретному посту), каноничексий URL
            # build_absolute_uri - строит полный URL адрес, включая HTTP схему и имя хоста
            post_url = request.build_absolute_uri(post.get_absolute_url())
            # Переменная, кот хранит тему письма
            subject = '{} ({}) recommends you reading "{}"'.format(cd['name'], cd['email'], post.title)
            # Переменная, кот хранит само письмо
            message = 'Read "{}" at {}\n\n{}\'s comments: {}'.format(post.title, post_url, cd['name'], cd['comments'])
            # Метод send_mail в качестве необходимых аргументов учитывает:
            # 1-тему письма, 2-сообщение, 3-отправителя, 4-список получателей
            send_mail(subject, message, 'admin@myblog.com', [cd['to']])
            # Присваиваем переменной sent значение True когда письмо было отправлено
            sent = True
        cd = form.cleaned_data
    # Если мы получаем запрос GET, то будет отбражаться пустая форма
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post,
                                                    'form': form,
                                                    'sent': sent,
                                                    'cd': cd})


# Использование базовых классов представлений(class-based views)
class PostListView(ListView):
    queryset = Post.objects.filter(status='published')
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'
