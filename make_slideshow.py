import Image
import sys
import subprocess

#resolution = (720, 480)
resolution = (1024, 768)
transition_frames = 18
slide_frames = 3*30
n_frames = transition_frames*2 + slide_frames

import ImageFont, ImageDraw, ImageStat
font=ImageFont.truetype("/usr/share/fonts/truetype/ttf-droid/DroidSans.ttf", 15)


class Slide:
	def __init__(self, filename, caption=None):
		self.filename=filename
		self.caption = caption
		self.n_frames = n_frames
		self.slide_frames = slide_frames
		
	def load(self):
		self.original = Image.open(self.filename)
		self.render_caption()
		
	def destroy(self):
		self.original = None
		self.overlay = None
		
	def render_caption(self):
		if self.caption:
			self.overlay = Image.new('RGBA', resolution, (0, 0, 0, 0))
			d = ImageDraw.Draw(self.overlay)
		
			textsize = d.textsize(self.caption, font=font)
			margin = (50, 10)
			padding = (8, 6)
			textpos = (margin[0]+padding[0], resolution[1]-margin[1]-padding[1]-textsize[1])
			rectangle = [(margin[0], resolution[1]-margin[1]-textsize[1]-2*padding[1]), (margin[0]+2*padding[0]+textsize[0], resolution[1]-margin[1])]
				
			color = '#fff'
			bcolor = (0, 0, 0, 140)
				
			d.rectangle(rectangle, fill=bcolor)
			d.text(textpos, self.caption, font=font, fill=color)
		else:
			self.overlay = None
	
	def draw_caption(self, im):
		if self.overlay:
			im.paste(self.overlay, (0, 0), self.overlay)

		
class StaticSlide(Slide):
	def load(self):
		Slide.load(self)
		self.original.thumbnail(resolution, Image.ANTIALIAS)
		if self.original.size != resolution:
			i = Image.new("RGB", resolution)
			xoffs = (resolution[0] - self.original.size[0])/2
			yoffs = (resolution[1] - self.original.size[1])/2
			i.paste(self.original, (xoffs,yoffs))
			self.original = i
		self.draw_caption(self.original)
			
	def frame(self, n):
		return self.original
		
class KenBurnsSlide(Slide):
	def __init__(self, filename, caption, start_scale, start_pos, end_scale, end_pos):
		Slide.__init__(self, filename, caption)
		self.start_scale = start_scale
		self.end_scale = end_scale
		self.start_pos = start_pos
		self.end_pos = end_pos
		#print self.__dict__
		
	def load(self):
		Slide.load(self)
		
		if float(self.original.size[0])/self.original.size[1] > float(resolution[0])/resolution[1]:
			width = self.original.size[0]
			height = self.original.size[0] * resolution[1] / resolution[0]
		else:
			height = self.original.size[1]
			width = self.original.size[1] * resolution[0] / resolution[1]
			
		#print self.original.size, width, height
		
		if self.original.size != (width, height):
			i = Image.new("RGB", (width, height))
			xoffs = (width - self.original.size[0])/2
			yoffs = (height - self.original.size[1])/2
			i.paste(self.original, (xoffs,yoffs))
			self.original = i
		
	def frame(self, n):
		progress = float(n)/self.n_frames
		
		def blendPoint(progress, p1, p2): return (p2[0]*progress + p1[0]*(1-progress), p2[1]*progress + p1[1]*(1-progress))
		scale = self.start_scale * (1-progress) + self.end_scale * progress
		pos = blendPoint(progress, self.start_pos, self.end_pos)
		
		width = self.original.size[0] * scale
		height = self.original.size[1] * scale
		center_x = self.original.size[0] * pos[0]
		center_y = self.original.size[1] * pos[1]
		
		#print ' ', scale, pos
		#print width, height, center_x, center_y
		#print (center_x - width/2.0, center_y - height/2.0, center_x + width/2.0, center_y + height/2.0)
		
		i = self.original.transform(resolution, Image.EXTENT, (center_x - width/2.0, center_y - height/2.0, center_x + width/2.0, center_y + height/2.0), Image.BICUBIC)
		#i = self.original.crop((center_x - width/2.0, center_y - height/2.0, center_x + width/2.0, center_y + height/2.0))
		#i = i.resize(resolution)
		self.draw_caption(i)
		return i
			
		
class BlackSlide:
	def __init__(self):
		self.slide_frames = 0
		
	def load(self):
		self.original = Image.new("RGB", resolution)
		
	def destroy(self):
		self.original = None
		
	def frame(self, n):
		return self.original
		
class Renderer:

	def __init__(self, l, fname):
		self.frameno = 0
		self.total_frames = transition_frames
		for i in l: 
			self.total_frames += i.slide_frames+transition_frames
	
		prevSlide = BlackSlide()
		prevSlide.load()
		l.append(BlackSlide())
	
		#self.dir = tempfile.mkdtemp('slideshow')
		#print self.dir
		#cmd = 'ffmpeg -v -1 -y -f image2pipe -vcodec ppm -i pipe: -r 30 -target ntsc-dvd "%s"'%fname
		cmd = 'ffmpeg -v -1 -y -f image2pipe -vcodec ppm -i pipe: -r 30 -b 5000k "%s"'%fname
		self.ffmpeg = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.pipe = self.ffmpeg.stdin
		self.ffmpeg.stdout.close()
		
		for slideno, slide in enumerate(l):
			self.message("Loading slide %i"%(slideno+1))
			slide.load()
			for i in xrange(transition_frames):
				self.message("Rendering transition (frame %i of %i)"%(i+1, transition_frames))
				self.output_frame(Image.blend(prevSlide.frame(i+transition_frames+prevSlide.slide_frames), slide.frame(i), float(i)/transition_frames))
			for i in xrange(slide.slide_frames):
				self.message("Rendering slide %i (frame %i of %i)"%(slideno+1, i+1, slide.slide_frames))
				self.output_frame(slide.frame(i+transition_frames))
			prevSlide.destroy()
			prevSlide = slide
		
		self.message("Finishing")
		print ""
		
	def output_frame(self, image):
		#image.save(os.path.join(self.dir, '%05d.ppm'%self.frameno), quality=95)
		#print self.frameno
		image.save(self.pipe, 'ppm')
		self.frameno+=1
		
	def message(self, m):
		s="\r[%3i%%] %s"%(100*self.frameno/self.total_frames, m)
		s += (80-len(s))*' '
		sys.stderr.write(s)
			
import pyexiv2
def datecaption(fname):
	try:
		i = pyexiv2.Image(fname)
		i.readMetadata()
		return i['Exif.Image.DateTime'].strftime('%B %Y')
	except:
		print "%s: no exif"%fname
		return ''
		
def importList(fname):
	l = []
	for line in open(fname):
		parts = line.strip().split('\t')
		#print parts
		fname = parts[0]
		if len(parts)>1:
			caption = parts[1].strip()
		else:
			caption=None
			
		if len(parts)>2:
			ss, sx, sy, es, ex, ey = [float(x) for x in parts[2].split(':')]
			l.append(KenBurnsSlide(fname, caption, ss, (sx, sy), es, (ex, ey)))
		else:
			l.append(StaticSlide(fname, caption))
	print "Loaded %i slides."%len(l)
	return l
		
def generateList(fname):
	f = open(fname, 'a')
	try:
		while True:
			line = raw_input()
			files = line.strip("\n '").split("' '")
			for i in files:
				f.write("%s\t%s\n"%(i, datecaption(i)))
	except EOFError:
		f.close()
		print "Exiting"
		
	

	

if __name__ == '__main__':
	from optparse import OptionParser
	
	parser = OptionParser()
	
	parser.add_option("-g", "--generate", dest="generate",
                  help="Take list of shell-quoted input on stdin and generate a list file output to FILE", metavar="FILE")
	parser.add_option("-r", "--render", dest="render", help="Render from the specified FILE", metavar="FILE")
	
	options, args = parser.parse_args()

	if options.generate:
		generateList(options.generate)
	elif options.render:
		Renderer(importList(options.render), args[0])
	else:
		parser.error('Need to specify action')

