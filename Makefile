CXXFLAGS?=-g -O3 -fPIC
DESTDIR=templates
OBJS=src/axis.o src/fifo.o src/m_axi.o src/trace.o
OUTPUTS=$(DESTDIR)/liblightningsimrt.a $(DESTDIR)/fifo.ll.jinja $(DESTDIR)/m_axi.ll.jinja $(DESTDIR)/axis.ll.jinja

.PHONY: all clean

all: $(OUTPUTS)

clean:
	rm -f $(OBJS) $(OUTPUTS)

$(DESTDIR)/liblightningsimrt.a: $(OBJS)
	$(AR) rcs $@ $^

$(DESTDIR)/%.ll.jinja: src/%.ll.jinja
	cp $< $@
