# Use official Nginx image
FROM nginx:alpine

# Remove default Nginx static files
RUN rm -rf /usr/share/nginx/html/*

# Copy your frontend files to Nginx public folder
COPY . /usr/share/nginx/html

# Expose port 80 inside the container
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
