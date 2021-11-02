import numpy as np
from warnings import warn

class util:
    """utility functions"""
    
    def _printchild(element,prefix):
        """
        recursive function for printing xml metadata with subelements
        """
        #if there are subelements, print and call itself on subelements
        if element:
            if element.attrib:
                print(prefix + element.tag + ' ' + str(element.attrib) + ':')
            else:
                print(prefix + element.tag + ':')
            for child in element:
                util._printchild(child,prefix=prefix+'   ')
        
        #otherwise, just print available info
        else:
            if not element.text:
                element.text = ''
            if not element.attrib:#if attributes are empty
                print(prefix + element.tag + ' = ' + element.text)
            elif 'unit' in element.attrib:#if not, get unit from attributes
                print(prefix + element.tag + ' = ' + element.text + ' ' + element.attrib['unit'])
            elif element.text:#when attributes not empty check if there is text
                print(prefix + element.tag + ' = ' + str(element.attrib) + element.text)
            else:
                print(prefix + element.tag + ' = ' + str(element.attrib))
    
    def print_metadata(xml_root):
        """
        print xml attributes/tags of phenom data to inspect elements.

        Parameters
        ----------
        xml_root : xml root object
            Takes output of get_metadata() and prints formatted metadata to the
            terminal
        """       
        print('-----------------------------------------------------')
        print('METADATA')
        print('-----------------------------------------------------')
        
        for element in xml_root:
            util._printchild(element,prefix='')
        
        print('-----------------------------------------------------\n')
        
    def image_histogram(image,binsize=1,log=True):
        """plot histogram of the image grey values
        
        Parameters
        ----------
        image : numpy.array-like
            the image to calculate the intensity histogram for.
        binsize : float-like, optional
            width (in intensity units) of the bins to use. The default is 1.
        log : bool, optional
            Whether to plot the histogram y axis on a log scale. The default is
            True.
        """
        import matplotlib.pyplot as plt
        minval = np.iinfo(image.dtype).min
        maxval = np.iinfo(image.dtype).max
        
        bins = np.linspace(minval,maxval,int((maxval-minval)/binsize))
        
        plt.figure()
        plt.hist(np.ravel(image),bins=bins,log=log)
        plt.xlabel('grey value')
        plt.ylabel('occurrence')
        plt.show(block=False)

import cv2
def _export_with_scalebar(exportim,pixelsize,unit,filename,crop=None,
                          resolution=None,draw_bar=True,barsize=None,scale=1,
                          loc=2,convert=None,font='arialbd.ttf',fontsize=16,
                          fontbaseline=0,fontpad=2,barthickness=16,barpad=10,
                          box=True,invert=False,boxalpha=0.6,boxpad=10):
    """
    see top level export_with_scalebar functions for docs
    """
    #imports
    import matplotlib.pyplot as plt
    from PIL import ImageFont, ImageDraw, Image
    
    #check color image
    if exportim.ndim > 2:
        if exportim.ndim == 3 and\
            (exportim.shape[2]==3 or exportim.shape[2]==4):
            warn('image looks like a color image, converting to greyscale')
            exportim = np.mean(exportim,axis=2)
        else:
            raise ValueError('image must be 2-dimensional')
    
    #normalize to 8 bit interval if not already uint8
    if exportim.dtype != np.uint8:
        print('normalizing to uint8 range')
        exportim = exportim.astype(float)
        exportim -= exportim.min()
        exportim *= 255.0/exportim.max()
        exportim = exportim.astype(np.uint8)
    
    #draw original figure before changing exportim
    fig,ax = plt.subplots(1,1)
    ax.imshow(exportim,cmap='gray',vmin=0,vmax=255)
    plt.title('original image')
    plt.axis('off')
    plt.tight_layout()
    
    #check if alternative form of cropping is used
    if not crop is None and len(crop) == 4:
        altcrop = True
    else:
        altcrop = False
    
    #print current axes limits for easy cropping
    def _on_lim_change(call):
        [txt.set_visible(False) for txt in ax.texts]
        xmin,xmax = ax.get_xlim()
        ymax,ymin = ax.get_ylim()
        if altcrop:
            croptext = 'current crop: ({:}, {:}, {:}, {:})'
            croptext = croptext.format(int(xmin),int(ymin),int(xmax-xmin+1),
                                       int(ymax-ymin+1))
        else:
            croptext = 'current crop: (({:}, {:}), ({:}, {:}))'
            croptext = croptext.format(int(xmin),int(ymin),int(xmax+1),
                                       int(ymax+1))
        ax.text(0.01,0.01,croptext,fontsize=12,ha='left',va='bottom',
                transform=ax.transAxes,color='red')
    
    #attach callback to limit change
    ax.callbacks.connect("xlim_changed", _on_lim_change)
    ax.callbacks.connect("ylim_changed", _on_lim_change)
    plt.show(block=False)
    
    #convert unit when drawing scalebar
    if draw_bar:
        if not convert is None and convert != unit:
            
            #always use mu for micrometer
            if convert == 'um':
                convert = 'µm'
            
            #check input against list of possible units
            units = ['pm','nm','µm','mm','m']
            if not unit in units:
                raise ValueError('"'+str(unit)+'" is not a valid unit')
            
            #factor 10**3 for every step from list, use indices to calculate
            pixelsize = pixelsize*10**(3*(units.index(unit)\
                                          -units.index(convert)))
            unit = convert
    
    #(optionally) crop
    if not crop is None:
        
        #if (x,y,w,h) format, convert to other format
        if len(crop) == 4:
            crop = ((crop[0],crop[1]),(crop[0]+crop[2],crop[1]+crop[3]))
        
        #crop
        exportim = exportim[crop[0][1]:crop[1][1],crop[0][0]:crop[1][0]]
        print('cropped to {:} × {:} pixels, {:.4g} × {:.4g} '.format(
            *exportim.shape,exportim.shape[0]*pixelsize,
            exportim.shape[1]*pixelsize)+unit)
    
    #set default scalebar to original scalebar or calculate len
    if type(barsize) == type(None):
        #take 15% of image width and round to nearest in list of 'nice' vals
        barsize = scale*0.15*exportim.shape[1]*pixelsize
        lst = [0.1,0.2,0.3,0.4,0.5,1,2,2.5,3,4,5,10,20,25,30,
               40,50,100,200,250,300,400,500,1000,2000,2500,
               3000,4000,5000,6000,8000,10000]
        barsize = lst[min(range(len(lst)), key=lambda i: abs(lst[i]-barsize))]
    
    #determine len of scalebar on im
    barsize_px = barsize/pixelsize
    
    #set default resolution or scale image and correct barsize_px
    if resolution is None:
        ny,nx = exportim.shape
        resolution = nx
    else:
        nx = resolution
        ny = int(exportim.shape[0]/exportim.shape[1]*nx)
        barsize_px = barsize_px/exportim.shape[1]*resolution
        exportim = cv2.resize(exportim, (int(nx),int(ny)), 
                              interpolation=cv2.INTER_AREA)
    
    #adjust general scaling for all sizes relative to 1024 pixels
    scale = scale*resolution/1024
    
    #can skip this whole part when not actually drawing the scalebar
    if draw_bar:

        #set up sizes
        barthickness = barthickness*scale
        boxpad = boxpad*scale
        barpad = barpad*scale
        fontpad = fontpad*scale
        fontsize = 2*fontsize*scale
        fontbaseline = fontbaseline*scale
        
        #format string
        if round(barsize)==barsize:
            text = str(int(barsize))+' '+unit
        else:
            for i in range(1,4):
                if round(barsize,i)==barsize:
                    text = ('{:.'+str(i)+'f} ').format(barsize)+unit
                    break
                elif i==3:
                    text = '{:.3f} '.format(round(barsize,3))+unit
    
        #get size of text
        #textsize = cv2.getTextSize(text, font, fontsize, int(fontthickness))[0]
        font = ImageFont.truetype(font,size=int(fontsize))
        textsize = ImageDraw.Draw(
            Image.fromarray(exportim)
        ).textsize(text,font=font)
        offset = font.getoffset(text)
        textsize = (textsize[0]+offset[0],textsize[1]+offset[1]+fontbaseline)    
        
        #correct baseline for mu in case of micrometer
        if unit=='µm':
            textsize = (textsize[0],textsize[1]-6*scale)
        
        #determine box size
        boxheight = barpad + barthickness + 2*fontpad + textsize[1]
        
        #determine box position based on loc
        #top left
        if loc == 0:
            x = boxpad
            y = boxpad
        #top right
        elif loc == 1:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = boxpad
        #bottom left
        elif loc == 2:
            x = boxpad
            y = ny - boxpad - boxheight
        #bottom right
        elif loc == 3:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = ny - boxpad - boxheight
        else:
            raise ValueError("loc must be 0, 1, 2 or 3 for top left, top right"
                             ", bottom left or bottom right respectively.")
        
        #put semitransparent box
        if box:
            #get rectangle from im and create box
            w,h = 2*barpad+max([barsize_px,textsize[0]]),boxheight
            subim = exportim[int(y):int(y+h), int(x):int(x+w)]
            white_box = np.ones(subim.shape, dtype=np.uint8) * 255
            
            #add or subtract box from im, and put back in im
            if invert:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 1-boxalpha, -white_box, boxalpha, 
                                    1.0)
            else:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 1-boxalpha, white_box, boxalpha, 
                                    1.0)
    
        #calculate positions for bar and text (horizontally centered in box)
        barx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 \
            - barsize_px/2
        bary = y+boxheight-barpad-barthickness
        textx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 \
            - textsize[0]/2
        texty = y + fontpad
        
        #color for bar and text
        if invert:
            color = 255
        else:
            color = 0
        
        #draw scalebar
        exportim = cv2.rectangle(
            exportim,
            (int(barx),int(bary)),
            (int(barx+barsize_px),int(bary+barthickness)),
            color,
            -1
        )
        
        #draw text
        exportim = Image.fromarray(exportim)
        draw = ImageDraw.Draw(exportim)
        draw.text(
            (textx,texty),
            text,
            fill=color,
            font=font
        )
        exportim = np.array(exportim)
    
    #show result
    plt.figure()
    plt.imshow(exportim,cmap='gray',vmin=0,vmax=255)
    plt.title('exported image')
    plt.axis('off')
    plt.tight_layout()
    plt.show(block=False)
    
    #save image
    cv2.imwrite(filename,exportim)
