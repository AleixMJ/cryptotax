# cryptotax v0.20 alpha
#### **Description:**


Cryptotax is a website application built with the Flask framework. The website allows you to manage your crypto currencies portfolio, check the markets and calculate the taxes of your transactions. The website is in the alpha product as it just reached MVP status. While in development more features will be added including different currencies and different types of tax calculations. The website gets the data from Coingecko API and is limited to 50 queries per minute in the free plan (which can be increased to a Pro plan in the future). The application is currently meant to be used on a PC as plenty of data is shown and might be challenging to fully analyse on a mobile (however, we may include mobile format in the future). Many libraries are used including; pandas (table management), werkzeug (store passwords as a hash for security) mplfinance (to draw the market charts), etc. Finally, bootstrap was used to build the website across all the hmlt tabs with a layout template and Jinja code.

The apps consist of the following folders/documents:

*__templates__:
This is where all the html websites are (basic Flask requirement).

*__static__:
This is where the chart images are saved and the CSS file.

*__app.py__:
This is the main Flask application where all the site routes and operations are carried.

*__functions.py__:
This is an extra python file with useful functions that the app.py uses.

*__cryptotax.db__:
This is the main SQlite database in which we store the data of all users. It has 3 tables at the moment; users, history and portfolio.

*__requirements.txt__:
This is the main file Fasks uses to know the requirements of the application.

*__Credits to__:

- Coingecko - providing API to obtain cryptocurrency data as requested.
- Bootstrap - provide a good infrastructure to speed up the development of the html files.


