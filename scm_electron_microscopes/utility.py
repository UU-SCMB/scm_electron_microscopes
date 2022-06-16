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
def _export_with_scalebar(exportim,pixelsize,unit,filename,preprocess=None,
        crop=None,intensity_range=None,resolution=None,draw_bar=True,
        barsize=None,scale=1,loc=2,convert=None,text=None,draw_text=True,
        font='arialbd.ttf',fontsize=16,fontbaseline=0,fontpad=2,
        barthickness=16,barpad=10,draw_box=True,invert=False,boxalpha=0.8,
        boxpad=10,save=True,show_figure=True,store_settings=False):
    """
    see top level export_with_scalebar functions for docs
    """
    #store all settings from locals before anything is changed or loaded
    if store_settings:
        items = locals()
        [items.pop(item) for item in ['exportim','pixelsize','unit']]
        #try and get source code for preprocess function instead of pointer
        if not preprocess is None:
            try:
                from inspect import getsource
                items['preprocess'] = ''.join(
                    '\n\t'+s for s in getsource(preprocess).split('\n')[:-1]
                )
            except (ImportError,NameError):
                pass
        #store to disk
        with open(filename.rpartition('.')[0]+'_settings.txt','w') as f:
            for key,val in items.items():
                if isinstance(val,str):
                    f.write(key+" = '"+val+"',\n")
                else:
                    f.write(key+" = "+str(val)+",\n")
    #imports
    import matplotlib.pyplot as plt
    if draw_bar or draw_text:
        from PIL import ImageFont, ImageDraw, Image
    
    #optionally call preprocess function
    if not preprocess is None:
        exportim = preprocess(exportim)

    #check color image
    if exportim.ndim > 2:
        if exportim.ndim == 3 and\
            (exportim.shape[2]==3 or exportim.shape[2]==4):
            warn('image looks like a color image, converting to greyscale')
            exportim = np.mean(exportim,axis=2)
        else:
            raise ValueError('image must be 2-dimensional')
    
    if show_figure:
        #draw original figure before changing exportim
        fig,ax = plt.subplots(1,1)
        ax.imshow(exportim,cmap='gray')
        plt.title('original image')
        plt.axis('off')
        plt.tight_layout()
    
        #check if alternative form of cropping is used
        altcrop = False
        if not crop is None:
            from matplotlib.patches import Rectangle
            if len(crop) == 4:
                crp = [c if c>=0 else s+c for s,c 
                       in zip(exportim.shape,crop[:2])] + list(crop[2:])
                altcrop = True
                x,y,w,h = crp
            else:
                crp = [[cc if cc>0 else s+cc for cc in c]\
                       for s,c in zip(exportim.shape,crop)]
                x,y = crp[0][0],crp[0][1]
                w,h = crp[1][0]-crp[0][0], crp[1][1]-crp[0][1]
            ax.add_patch(Rectangle((x,y),w,h,ec='r',fc='none'))
    
        #print current axes limits for easy cropping
        def _on_lim_change(call):
            [txt.set_visible(False) for txt in ax.texts]
            xmin,xmax = ax.get_xlim()
            ymax,ymin = ax.get_ylim()
            if altcrop:
                croptext = 'current crop: ({:}, {:}, {:}, {:})'
                croptext = croptext.format(int(xmin),int(ymin),
                                           int(xmax-xmin+1),int(ymax-ymin+1))
            else:
                croptext = 'current crop: (({:}, {:}), ({:}, {:}))'
                croptext = croptext.format(int(xmin),int(ymin),
                                           int(xmax+1),int(ymax+1))
            ax.text(0.01,0.01,croptext,fontsize=12,ha='left',va='bottom',
                    transform=ax.transAxes,color='red')
        
        #attach callback to limit change
        ax.callbacks.connect("xlim_changed", _on_lim_change)
        ax.callbacks.connect("ylim_changed", _on_lim_change)
        plt.show(block=False)
    
    #convert unit
    if not convert is None and convert != unit and (draw_bar or draw_text):
        
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
            exportim.shape[1],exportim.shape[0],exportim.shape[1]*pixelsize,
            exportim.shape[0]*pixelsize)+unit)
    
    #get intensity range for None or automatic options
    if intensity_range is None:#min and max
        intensity_range = (exportim.min(),exportim.max())
    elif intensity_range == 'auto' or intensity_range == 'automatic':
        intensity_range = (
            np.percentile(exportim,0.01),
            np.percentile(exportim,99.99)
        )
    elif not type(intensity_range) in [tuple,list] or len(intensity_range)!=2:
        raise TypeError("`intensity_range` must be None, 'automatic' or "
                        "2-tuple of values")
    
    #rescale the intensity without int overflow
    imin, imax = intensity_range
    exportim[exportim < imin] = imin  
    exportim[:,:] = exportim[:,:] - imin
    imax = imax - imin
    mask = exportim < imax
    exportim[~mask] = 255
    exportim[mask] = exportim[mask]*(255/imax)
    
    #convert datatype if not already uint8
    if exportim.dtype != np.uint8:
        exportim = exportim.astype(np.uint8)
    
    #set default scalebar to original scalebar or calculate len
    if barsize is None:
        #take 15% of image width and round to nearest in list of 'nice' vals
        barsize = scale*0.12*exportim.shape[1]*pixelsize
        lst = [
            0.01, 0.02, 0.025, 0.03, 0.04, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5,
            1, 2, 2.5, 3, 4, 5, 10, 20, 25, 30, 40, 50, 100, 200, 250, 300,
            400, 500, 1000, 2000, 2500, 3000, 4000, 5000, 6000, 8000, 10000
        ]
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
    
    #can skip this whole part when not actually drawing the scalebar
    if draw_bar or draw_text:
        
        #adjust general scaling for all sizes relative to 1024 pixels
        scale = scale*resolution/1024

        #set up sizes
        barthickness = barthickness*scale
        boxpad = boxpad*scale
        barpad = barpad*scale
        
        if draw_text:
            fontpad = fontpad*scale
            fontsize = 2*fontsize*scale
            fontbaseline = fontbaseline*scale
            
            #define text to write as size of the scalebar, account for precision
            if text is None:
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
            font = ImageFont.truetype(font,size=int(fontsize))
            textsize = ImageDraw.Draw(Image.fromarray(exportim)).textsize(
                text,font=font)
            
            offset = font.getoffset(text)
            textsize = (textsize[0]+offset[0],textsize[1]+offset[1]+fontbaseline)    
            
            #correct baseline for mu in case of micrometer
            if 'µ' in text:
                textsize = (textsize[0],textsize[1]-6*scale)
        
        else:
            textsize = (0,0)
            fontpad = 0
        
        #determine box height with appropriate paddings
        if draw_text and draw_bar:#both
            boxheight = barpad + barthickness + 2*fontpad + textsize[1]
            boxwidth = max([2*barpad+barsize_px,2*fontpad+textsize[0]])
        elif draw_bar:#bar only
            boxheight = 2*barpad + barthickness
            boxwidth = 2*barpad+barsize_px
        else:#text only
            boxheight = 2*fontpad + textsize[1]
            boxwidth = 2*fontpad + textsize[0]
        
        #determine box/bar/text position based on loc
        #top left
        if loc == 0:
            x = boxpad
            y = boxpad
        #top right
        elif loc == 1:
            x = nx - boxpad - boxwidth
            y = boxpad
        #bottom left
        elif loc == 2:
            x = boxpad
            y = ny - boxpad - boxheight
        #bottom right
        elif loc == 3:
            x = nx - boxpad - boxwidth
            y = ny - boxpad - boxheight
        else:
            raise ValueError("loc must be 0, 1, 2 or 3 for top left, top right"
                             ", bottom left or bottom right respectively.")
        
        #put semitransparent box
        if draw_box:
            #get rectangle from im and create box
            subim = exportim[int(y):int(y+boxheight), int(x):int(x+boxwidth)]
            white_box = np.ones(subim.shape, dtype=np.uint8) * 255
            
            #add or subtract box from im, and put back in im
            if invert:
                exportim[int(y):int(y+boxheight), int(x):int(x+boxwidth)] = \
                    cv2.addWeighted(subim, 1-boxalpha, -white_box, boxalpha, 
                                    1.0)
            else:
                exportim[int(y):int(y+boxheight), int(x):int(x+boxwidth)] = \
                    cv2.addWeighted(subim, 1-boxalpha, white_box, boxalpha, 
                                    1.0)
    
        #color for bar and text
        if invert:
            color = 255
        else:
            color = 0
            
        if draw_bar:
            #calculate positions for bar
            barx = (2*x + boxwidth)/2 - barsize_px/2
            bary = y+boxheight-barpad-barthickness
        
            #draw scalebar
            exportim = cv2.rectangle(
                exportim,
                (int(barx),int(bary)),
                (int(barx+barsize_px),int(bary+barthickness)),
                color,
                -1
            )
        
        if draw_text:
            textx = (2*x + boxwidth)/2 - textsize[0]/2
            texty = y + fontpad
        
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
    if show_figure:
        plt.figure()
        plt.imshow(exportim,cmap='gray',vmin=0,vmax=255)
        plt.title('exported image')
        plt.axis('off')
        plt.tight_layout()
        plt.show(block=False)
    
    #save image
    if save:
        cv2.imwrite(filename,exportim)

    return exportim