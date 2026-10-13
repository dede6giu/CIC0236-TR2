import matplotlib.pyplot as plt
import numpy as np
import util
import configurations as cfg

def singleColumnLine(csvFileName: str, column: tuple, *, showGraphs: bool = True):
    # Pegar valores
    x = util.list_from_csv_column(csvFileName, 0)
    y = util.list_from_csv_column(csvFileName, column[0])
    nx = (np.asarray(x)).astype(int)
    ny = (np.asarray(y)).astype(column[1])

    # Plot
    plt.style.use('_mpl-gallery')
    fig, ax = plt.subplots()
    ax.plot(nx, ny)
    ax.set(xlabel='segment',
            ylabel=f'{column[2]}')

    fig.set_size_inches((1200/fig.dpi, 900/fig.dpi))
    fig.set_layout_engine('tight')

    fig.savefig(cfg.filePathBase + csvFileName + f"_{column[2]}" + ".png")
    if showGraphs:
        plt.show(block=False)
        plt.pause(0.001)