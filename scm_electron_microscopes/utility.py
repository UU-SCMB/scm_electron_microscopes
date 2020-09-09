import numpy as np
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
