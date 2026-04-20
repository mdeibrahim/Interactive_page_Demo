from content.models import Category, SubCategory, Module, CourseVideo

cat_slug = 'dummy-category'
cat, created = Category.objects.get_or_create(name='Dummy Category', slug=cat_slug)

courses = [
    {"name":"Dummy Course Alpha", "slug":"dummy-course-alpha", "price":150, "desc":"Alpha dummy course"},
    {"name":"Dummy Course Beta", "slug":"dummy-course-beta", "price":200, "desc":"Beta dummy course"},
    {"name":"Dummy Course Gamma", "slug":"dummy-course-gamma", "price":120, "desc":"Gamma dummy course"},
]

for c in courses:
    sc, created = SubCategory.objects.get_or_create(category=cat, slug=c["slug"], defaults={"name":c["name"], "description":c["desc"], "price":c["price"]})
    sc.name = c["name"]
    sc.description = c["desc"]
    sc.price = c["price"]
    sc.save()

    module, mcreated = Module.objects.get_or_create(subcategory=sc, slug='module-1', defaults={"title":"Module 1", "description":"Module 1 for "+c["name"], "order":1})
    module.title = "Module 1"
    module.description = "Module 1 for " + c["name"]
    module.save()

    video, vcreated = CourseVideo.objects.get_or_create(module=module, title='Intro Video', defaults={"video_url":"https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4", "duration_seconds":300, "order":1})
    video.duration_seconds = 300
    video.order = 1
    video.save()

    print('CREATED:', sc.slug, sc.price, 'module:', module.slug, 'video_id:', video.id)
