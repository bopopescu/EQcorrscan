#!/usr/bin/python
"""
Utility code for most of the plots used as part of the EQcorrscan package.
"""
import numpy as np
import matplotlib.pylab as plt
def triple_plot(cccsum, trace, threshold, save=False, savefile=''):
    """
    Main function to make a triple plot with a day-long seismogram, day-long
    correlation sum trace and histogram of the correlation sum to show normality

    :type cccsum: numpy.array
    :type trace: obspy.Trace
    :type threshold: float
    :type save: Bool, optional
    :type savefile: String, optional
    """
    if len(cccsum) != len(trace.data):
        print 'cccsum is: '+str(len(cccsum))+' trace is: '+str(len(trace.data))
        raise ValueError('cccsum and trace must have the same number of data points')
    df = trace.stats.sampling_rate
    npts = trace.stats.npts
    t = np.arange(npts, dtype=np.float32) / (df*3600)
    # Generate the subplot for the seismic data
    ax1 = plt.subplot2grid((2,5), (0,0), colspan=4)
    ax1.plot(t, trace.data, 'k')
    ax1.axis('tight')
    ax1.set_ylim([-100,100])
    # Generate the subplot for the correlation sum data
    ax2 = plt.subplot2grid((2,5), (1,0), colspan=4, sharex=ax1)
    # Plot the threshold values
    ax2.plot([min(t), max(t)], [threshold, threshold], color='r', lw=1, label="Threshold")
    ax2.plot([min(t), max(t)], [-threshold,-threshold], color='r', lw=1)
    ax2.plot(t, cccsum, 'k')
    ax2.axis('tight')
    ax2.set_ylim([-5, 5])
    ax2.set_xlabel("Time after %s [hr]" % trace.stats.starttime.isoformat())
    # ax2.legend()
    # Generate a small subplot for the histogram of the cccsum data
    ax3 = plt.subplot2grid((2,5), (1,4), sharey=ax2)
    ax3.hist(cccsum, 200, normed=1, histtype='stepfilled', \
             orientation='horizontal', color='black')
    ax3.set_ylim([-5, 5])
    fig=plt.gcf()
    fig.suptitle(trace.id)
    fig.canvas.draw()
    if not save:
        plt.show()
    else:
        plt.savefig(savefile)
    return

def peaks_plot(correlations, starttime, samp_rate, save=False, peaks=[(0,0)], \
               savefile=''):
    """
    Simple utility code to plot the correlation peaks to check that the peak
    finding routine is running correctly, used in debugging for the EQcorrscan
    module.

    :type correlations: numpy.array
    :type starttime: obspy.UTCDateTime
    :type samp_rate: float
    :type save: Boolean, optional
    :type peaks: List of Tuple, optional
    :type savefile: String, optional
    """
    npts=len(correlations)
    t = np.arange(npts, dtype=np.float32) / (samp_rate*3600)
    fig=plt.figure()
    ax1=fig.add_subplot(111)
    ax1.plot(t, correlations, 'k')
    ax1.scatter(peaks[0][1]/(samp_rate*3600),abs(peaks[0][0]),color='r', label='Peaks')
    for peak in peaks:
        ax1.scatter(peak[1]/(samp_rate*3600),abs(peak[0]),color='r')
    ax1.legend()
    ax1.set_xlabel("Time after %s [hr]" % starttime.isoformat())
    ax1.axis('tight')
    fig.suptitle('Correlation peaks')
    if not save:
        plt.show()
    else:
        plt.savefig(savefile)
    return

def cumulative_detections(dates, template_names, save=False, savefile=''):
    """
    Simple plotting function to take a list of UTCDateTime objects and plot
    a cumulative detections list.  Can take dates as a list of lists and will
    plot each list seperately, e.g. if you have dates from more than one
    template it will overlay them in different colours.

    :type dates: list of lists of datetime.datetime
    :param dates: Must be a list of lists of datetime.datetime objects
    :type template_names: list of strings
    :param template_names: List of the template names in order of the dates
    :type save: Boolean, optional
    :type savefile: String, optional
    """
    # Set up a default series of parameters for lines
    colors=['blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black', \
            'firebrick', 'purple', 'darkgoldenrod', 'gray']
    linestyles=['-','-.', '--', ':']
    # Check that dates is a list of lists
    if type(dates[0]) != list:
        dates=[dates]
    i=0
    j=0
    k=0
    plothandles=[]
    for template_dates in dates:
        template_dates.sort()
        counts=np.arange(0,len(template_dates))
        filename,=plt.plot(template_dates,counts, linestyles[j], \
                           color=colors[i], label=template_names[k],\
                           linewidth=3.0)
        k+=1
        plothandles.append(filename)
        if i < len(colors):
            i+=1
        else:
            i=0
            j+=1
    plt.xlabel('Date')
    plt.ylabel('Cumulative detections')
    plt.title('Cumulative detections for all templates')
    plt.legend()#handles=plothandles)
    if save:
        plt.savefig(savefile)
    else:
        plt.show()
    return