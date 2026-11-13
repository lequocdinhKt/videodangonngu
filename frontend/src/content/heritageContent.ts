import type { LanguageCode, Video } from '../types'
import overviewThumbnail from '../assets/ma-nhai-overview.jpg'
import inscriptionThumbnail from '../assets/ma-nhai-inscription.jpg'

type LocalizedText = Record<LanguageCode, string>

export interface HeritageChapter {
  number: string
  slug: string
  productionVideoId: string | null
  route: string
  menuLabel: LocalizedText
  title: LocalizedText
  description: LocalizedText
  thumbnail: string
}

export const HERITAGE_COPY: Record<LanguageCode, {
  siteName: string
  welcome: string
  eyebrow: string
  introduction: string
  explore: string
  exploreHint: string
  menu: string
  home: string
  chapter: string
  watch: string
  next: string
}> = {
  'vi-VN': {
    siteName: 'Ma nhai Ngũ Hành Sơn',
    welcome: 'Chào mừng bạn đến với Ngũ Hành Ma Nhai!',
    eyebrow: 'HÀNH TRÌNH KHÁM PHÁ',
    introduction: 'Khám phá những văn tự được khắc trực tiếp trên vách đá và hang động Ngũ Hành Sơn - nơi lưu giữ nhiều lớp ký ức về lịch sử, văn hóa và giao lưu quốc tế.',
    explore: 'Chọn nội dung khám phá',
    exploreHint: 'Mỗi mục là một video ngắn. Bạn có thể bật, tắt hoặc đổi ngôn ngữ phụ đề ngay trong trình phát.',
    menu: 'Danh mục',
    home: 'Trang chủ',
    chapter: 'Nội dung',
    watch: 'Xem video',
    next: 'Nội dung tiếp theo',
  },
  'en-US': {
    siteName: 'Ma Nhai - Marble Mountains',
    welcome: 'A welcome from the heritage site',
    eyebrow: 'A HERITAGE JOURNEY',
    introduction: 'Discover the inscriptions carved into the cliffs and caves of the Marble Mountains, preserving layers of history, culture and international exchange.',
    explore: 'Choose a story to explore',
    exploreHint: 'Each chapter is a short video. Subtitles can be turned on, off or changed inside the player.',
    menu: 'Contents',
    home: 'Home',
    chapter: 'Chapter',
    watch: 'Watch video',
    next: 'Next chapter',
  },
  'ru-RU': {
    siteName: 'Ма-Няй в Мраморных горах',
    welcome: 'Приветствие от объекта наследия',
    eyebrow: 'ПУТЕШЕСТВИЕ ПО НАСЛЕДИЮ',
    introduction: 'Познакомьтесь с надписями на скалах и в пещерах Мраморных гор, которые хранят память об истории, культуре и международных связях.',
    explore: 'Выберите тему',
    exploreHint: 'Каждая тема представлена коротким видео. Субтитры можно включить, выключить или сменить в плеере.',
    menu: 'Содержание',
    home: 'Главная',
    chapter: 'Раздел',
    watch: 'Смотреть видео',
    next: 'Следующая тема',
  },
  'zh-CN': {
    siteName: '五行山摩崖石刻',
    welcome: '来自文化遗产的问候',
    eyebrow: '文化遗产之旅',
    introduction: '探索五行山峭壁与洞窟中的摩崖石刻，了解这里保存的历史、文化与国际交流记忆。',
    explore: '选择探索内容',
    exploreHint: '每个主题都是一段短片，您可以在播放器中开启、关闭或切换字幕语言。',
    menu: '目录',
    home: '首页',
    chapter: '内容',
    watch: '观看视频',
    next: '下一内容',
  },
}

export const PROJECT_INTRO: Record<LanguageCode, string[]> = {
  'vi-VN': [
    'Ma nhai tại di tích danh thắng Ngũ Hành Sơn là một di sản tư liệu vô cùng độc đáo thuộc Chương trình Ký ức Thế giới được UNESCO công nhận. Tuy nhiên, di sản này vẫn chưa thực sự được cộng đồng biết đến rộng rãi, khiến nhiều tư liệu quý về lịch sử, tôn giáo, địa lý, văn học, ngôn ngữ và nghệ thuật chưa thể lan tỏa trọn vẹn đến công chúng.',
    'Dự án đem đến những kiến thức dễ tiếp cận bằng các video tư liệu thuyết minh sinh động kết hợp phụ đề đa ngôn ngữ, góp phần bảo tồn giá trị văn hóa truyền thống, thúc đẩy du lịch thông minh và lan tỏa niềm tự hào di sản đến cộng đồng.',
  ],
  'en-US': [
    'The Ma Nhai inscriptions at the Marble Mountains are a distinctive documentary heritage recognized by UNESCO’s Memory of the World programme.',
    'Through narrated documentary videos and multilingual subtitles, this project makes their history, culture and artistic value easier for local communities and international visitors to explore.',
  ],
  'ru-RU': [
    'Надписи Ма-Няй в Мраморных горах — уникальное документальное наследие, включённое в программу ЮНЕСКО «Память мира».',
    'Документальные видео и многоязычные субтитры помогают жителям и зарубежным гостям ближе познакомиться с их исторической и культурной ценностью.',
  ],
  'zh-CN': [
    '五行山摩崖石刻是被列入联合国教科文组织“世界记忆”计划的独特文献遗产。',
    '本项目通过生动的纪录短片与多语言字幕，让本地居民和国际游客更容易了解其历史、文化与艺术价值。',
  ],
}

export const DECODE_COPY: Record<LanguageCode, {
  eyebrow: string
  title: string
  question: string
  hint: string
  result: string
}> = {
  'vi-VN': {
    eyebrow: 'CHUYÊN ĐỀ · GIẢI MÃ DI SẢN',
    title: 'Giải mã ma nhai',
    question: 'Bạn đang tò mò về câu chuyện của bia ma nhai nào tại Ngũ Hành Sơn?',
    hint: '',
    result: 'Video phân tích',
  },
  'en-US': {
    eyebrow: 'FEATURE · DECODING HERITAGE',
    title: 'Decoding Ma Nhai',
    question: 'What do the inscriptions reveal about the history and cultural exchange of the Marble Mountains?',
    hint: 'Choose a video to explore the story, chronology and layers of meaning preserved in each inscription.',
    result: 'Analysis video',
  },
  'ru-RU': {
    eyebrow: 'СПЕЦТЕМА · РАСШИФРОВКА НАСЛЕДИЯ',
    title: 'Расшифровка Ма-Няй',
    question: 'Что каменные надписи рассказывают об истории и культурных связях Мраморных гор?',
    hint: 'Выберите видео, чтобы узнать историю, датировку и смысл каждого памятника.',
    result: 'Видеоразбор',
  },
  'zh-CN': {
    eyebrow: '专题 · 解码文化遗产',
    title: '解码摩崖石刻',
    question: '石刻文字如何讲述五行山的历史与文化交流？',
    hint: '选择视频，深入了解每方碑刻所保存的故事、年代与文化内涵。',
    result: '解析视频',
  },
}

export const HERITAGE_CHAPTERS: HeritageChapter[] = [
  {
    number: '01',
    slug: 'hoi-an',
    productionVideoId: null,
    route: '/videos/hoi-an',
    menuLabel: {
      'vi-VN': 'Tổng quan Ma nhai Ngũ Hành Sơn',
      'en-US': 'Overview of Ma Nhai inscriptions',
      'ru-RU': 'Обзор надписей Ма-Няй',
      'zh-CN': '五行山摩崖石刻概览',
    },
    title: {
      'vi-VN': 'Ma Nhai Ngũ Hành Sơn - Khám phá hệ thống bia đá và những hang động huyền bí',
      'en-US': 'Marble Mountains’ Ma Nhai Inscriptions - Exploring the stone inscriptions and mysterious caves',
      'ru-RU': 'Ма-Няй в Мраморных горах - знакомство с системой каменных надписей и таинственными пещерами',
      'zh-CN': '五行山摩崖石刻 - 探索石刻体系与神秘洞窟',
    },
    description: {
      'vi-VN': 'Bức tranh tổng quan về hệ thống văn tự cổ được lưu lại trên vách đá và trong các hang động tại danh thắng Ngũ Hành Sơn.',
      'en-US': 'An introduction to the historic inscriptions preserved on the cliffs and inside the caves of the Marble Mountains.',
      'ru-RU': 'Знакомство с историческими надписями, сохранившимися на скалах и в пещерах Мраморных гор.',
      'zh-CN': '整体介绍五行山峭壁与洞窟中保存至今的历史石刻。',
    },
    thumbnail: overviewThumbnail,
  },
  {
    number: '02',
    slug: 'giai-ma-ma-nhai',
    productionVideoId: '5216c345-5779-4549-9439-22c6b5a0e760',
    route: '/giai-ma-ma-nhai',
    menuLabel: {
      'vi-VN': 'Giải mã ma nhai',
      'en-US': 'Decoding Ma Nhai',
      'ru-RU': 'Расшифровка Ма-Няй',
      'zh-CN': '解码摩崖石刻',
    },
    title: {
      'vi-VN': '“Phổ Đà Sơn Linh Trung Phật” - Dấu ấn giao thoa văn hóa Việt - Nhật - Trung từ năm 1640',
      'en-US': '“Phổ Đà Sơn Linh Trung Phật” - A testament to Vietnamese, Japanese and Chinese cultural exchange since 1640',
      'ru-RU': '«Фо-да-шон-линь-чунг-фат» - свидетельство культурного обмена между Вьетнамом, Японией и Китаем с 1640 года',
      'zh-CN': '“普陀山灵中佛” - 见证自1640年以来越南、日本与中国的文化交融',
    },
    description: {
      'vi-VN': 'Đi sâu vào một bia ma nhai tiêu biểu và câu chuyện giao lưu văn hóa được lưu dấu qua gần bốn thế kỷ.',
      'en-US': 'A closer look at a remarkable inscription and the story of cultural exchange it has carried for nearly four centuries.',
      'ru-RU': 'Подробный рассказ о выдающейся надписи и истории культурного обмена, сохраненной почти четыре столетия.',
      'zh-CN': '深入了解一方代表性摩崖碑刻，以及它近四百年来所承载的文化交流故事。',
    },
    thumbnail: inscriptionThumbnail,
  },
]

export function getHeritageChapter(slug: string | undefined): HeritageChapter | undefined {
  return HERITAGE_CHAPTERS.find(item => item.slug === slug)
}

export function getHeritageChapterForProductionVideo(videoId: string): HeritageChapter | undefined {
  return HERITAGE_CHAPTERS.find(item => item.productionVideoId === videoId)
}

export function localizeHeritageVideo(video: Video, language: LanguageCode): Video {
  const chapter = getHeritageChapterForProductionVideo(video.id)
  if (!chapter) return video
  return {
    ...video,
    title: chapter.title[language],
    description: chapter.description[language],
    thumbnail_url: chapter.thumbnail,
  }
}
