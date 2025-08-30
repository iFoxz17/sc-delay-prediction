FROM public.ecr.aws/lambda/python:3.13

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt requirements-no-deps.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --no-deps -r requirements-no-deps.txt

# Add and run the Python cleanup script
COPY clean_site_packages.py .
RUN python clean_site_packages.py && rm clean_site_packages.py

COPY estimator/ ${LAMBDA_TASK_ROOT}/estimator
COPY rt_estimator_handler.py ${LAMBDA_TASK_ROOT}

CMD ["rt_estimator_handler.handler"]
