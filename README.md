# We Give

  We Give is a nonprofit micro-donations and virtual gift service created to help
  raise donations and awareness for small, grassroots charities.

## Status

  The We Give project, including both the underlying technical code as well as the
  nonprofit organization, has been dormant for a period of over a year.  Reasons
  include:
  
  * Uptake of the service was slow due to the barrier posed by Amazon Payments accounts, required by We Give for making a donation
  * Facebook's transition away from application box content featured on user profiles

## The Technology

  This service uses the following tech stack:
  
  * [Pylons](https://docs.pylonsproject.org/projects/pylons_framework/dev/) (Python) web framework, version 0.9.7
    * [Mako](http://www.makotemplates.org/) template engine
    * [SQLAlchemy](http://www.sqlalchemy.org/)
  * Facebook - canvas application API, some old version from 2009
    * [PyFacebook](https://github.com/sciyoshi/pyfacebook/) - Python Facebook library, also some old version, from when it was hosted [here](http://code.google.com/p/pyfacebook/).
  * MySQL
  * Amazon Web Services
    * [EC2](http://aws.amazon.com/ec2/)
    * [S3](http://aws.amazon.com/s3/)
    * [FPS](http://aws.amazon.com/fps/) - Flexible Payments System
  * [RightScale](http://www.rightscale.com/) - using their [free Developer account](https://www.rightscale.com/products/plans-pricing/) to automate deployment to AWS
