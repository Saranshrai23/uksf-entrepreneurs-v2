# UKSF Entrepreneur QR Profile Application – Dev POC

## 1. Introduction

The UKSF Entrepreneur QR Profile Application is a web-based application designed to create and manage individual member profiles.

Each user can create a profile containing information such as name, designation, company details, contact information, LinkedIn profile and profile photograph. After profile creation and admin approval, the application generates a unique QR code for the user.

When the QR code is scanned, the user's public profile page opens directly in the browser.

The application also provides an **Admin Panel** through which an administrator can review profiles, approve new profiles, edit/manage existing records and delete profiles when required.

---

## 2. Purpose of the POC

The purpose of this POC is to demonstrate an end-to-end application deployment where:

* Users can create their own profiles.
* Missing information can remain blank during initial profile creation.
* Users can later update their profile information.
* Users can upload their own profile photographs.
* Each profile gets a unique URL.
* A unique QR code is generated for every approved profile.
* Profile photographs and QR codes are stored persistently in Amazon S3.
* Profile information is stored in PostgreSQL.
* New user profiles can be approved by an administrator.
* The administrator can delete unwanted or invalid profiles.
* The application is deployed automatically using Jenkins.
* Docker images are stored in Amazon ECR.
* Users access the application through an AWS Application Load Balancer.

---

## 3. Application Architecture

```text
                         User / Admin
                              |
                              |
                              v
                     Application Load Balancer
                              |
                              v
                        EC2 Instance
                      Docker Container
                              |
                 +------------+-------------+
                 |                          |
                 v                          v
          PostgreSQL RDS                  Amazon S3
          Profile Details            Photos + QR Codes
                 |
                 |
                 v
         Users / Admin Records


CI/CD Flow

GitHub
   |
   v
Local Jenkins
   |
   +---- Docker Build
   |
   +---- Push Image
   v
Amazon ECR
   |
   v
Deploy on EC2
```

---

## 4. AWS Architecture

The Dev environment uses a simple AWS architecture suitable for a POC.

```text
AWS VPC
10.20.0.0/16
│
├── Public Subnet A
│      |
│      └── EC2 Application Server
│
├── Public Subnet B
│
│
├── Application Load Balancer
│      |
│      └── EC2 :8000
│
├── Private DB Subnet A
│      |
│      └── PostgreSQL RDS
│
└── Private DB Subnet B


Additional AWS Services

Amazon ECR
   └── Docker Images

Amazon S3
   ├── Profile Photos
   └── QR Codes

IAM
   └── EC2 permissions for S3 and ECR
```

The PostgreSQL database is not publicly accessible. Only the EC2 application server is allowed to connect to PostgreSQL on port `5432`.

---

## 5. Technology Stack

| Component          | Technology                    |
| ------------------ | ----------------------------- |
| Application        | Python Web Application        |
| Web Server         | Uvicorn                       |
| Application Port   | 8000                          |
| Containerization   | Docker                        |
| Database           | PostgreSQL                    |
| Managed Database   | Amazon RDS                    |
| Object Storage     | Amazon S3                     |
| Container Registry | Amazon ECR                    |
| Compute            | Amazon EC2                    |
| Load Balancer      | AWS Application Load Balancer |
| Infrastructure     | Terraform                     |
| CI/CD              | Jenkins                       |
| Source Code        | GitHub                        |
| QR Generation      | Python QR Code Library        |
| AWS SDK            | Boto3                         |

---

## 6. Infrastructure Provisioning

Terraform is used to create the complete Dev infrastructure.

The Terraform configuration provisions:

```text
VPC
Public Subnets
Private Database Subnets
Internet Gateway
Route Tables
Security Groups
EC2 Instance
Application Load Balancer
Target Group
PostgreSQL RDS
Amazon S3 Bucket
Amazon ECR Repository
IAM Role
IAM Instance Profile
EC2 SSH Key
```

Using Terraform allows the complete environment to be reproduced using infrastructure-as-code rather than manually creating AWS resources.

The main Terraform workflow is:

```bash
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

---

## 7. Application Deployment Flow

The application deployment is automated through Jenkins.

Jenkins is hosted locally and does not run inside AWS.

The deployment flow is:

```text
Developer
    |
    v
GitHub
    |
    v
Local Jenkins
    |
    v
Docker Build
    |
    v
Amazon ECR
    |
    v
EC2 Docker Pull
    |
    v
Start Application Container
    |
    v
Application Load Balancer
    |
    v
User
```

### Jenkins Pipeline Stages

The Jenkins pipeline contains the following stages:

```text
Checkout
   ↓
Build Docker Image
   ↓
Login to ECR
   ↓
Push Docker Image
   ↓
Find Dev EC2
   ↓
SSH into EC2
   ↓
Pull Latest Docker Image
   ↓
Stop Previous Container
   ↓
Start New Container
   ↓
Health Check
```

This provides a simple automated CI/CD deployment mechanism for the Dev POC.

---

## 8. Profile Creation Flow

When a new member joins the organisation, the user can create a profile through the web application.

```text
New User
   |
   v
Create Profile Page
   |
   v
Enter Information
   |
   +---- Name
   +---- Designation
   +---- Company
   +---- Email
   +---- Phone
   +---- LinkedIn
   +---- Other Information
   |
   v
Upload Photo
   |
   v
Submit Profile
   |
   v
Pending Admin Approval
```

The application does not need to fill missing information using dummy or placeholder values.

If any information is unavailable, the respective field remains blank.

The user can add or update that information later.

---

## 9. Admin Approval Functionality

A newly created profile does not need to become publicly available immediately.

Instead, its status can remain:

```text
Pending
```

The administrator reviews the profile from the Admin Panel.

The administrator can then approve it.

```text
User Creates Profile
        |
        v
     Pending
        |
        v
   Admin Review
        |
        v
     Approve
        |
        v
   Active Profile
        |
        v
   QR Generated
```

This prevents unwanted or incorrect profiles from being published automatically.

---

## 10. Admin Panel

The application contains an Admin Panel where administrators can manage the profiles.

Example:

```text
--------------------------------------------------------------

UKSF Admin Panel

--------------------------------------------------------------

Name             Status       Actions

Saransh Rai      Approved     View | Edit | Delete

John Smith       Pending      View | Approve | Delete

Rahul Kumar      Approved     View | Edit | Delete

--------------------------------------------------------------
```

The administrator can perform operations such as:

* View a profile
* Approve a profile
* Edit/manage profile information
* Delete a profile

---

## 11. Admin Delete Profile Functionality

A **Delete button** is provided in the Admin Panel.

Only an authenticated administrator is allowed to delete profiles.

Example:

```text
Profile

Saransh Rai
Software Engineer

[ View ]   [ Edit ]   [ Delete ]
```

When the administrator clicks:

```text
Delete
```

the application sends a delete request for the selected profile.

Conceptually:

```text
Admin
   |
   v
Admin Dashboard
   |
   v
Click Delete
   |
   v
DELETE Profile Request
   |
   v
Application Backend
   |
   +---- Verify Admin
   |
   +---- Find Profile
   |
   +---- Delete Database Record
   |
   +---- Delete associated S3 objects
   |
   v
Profile Removed
```

This functionality ensures administrators have full control over invalid, duplicate or outdated profiles.

---

## 12. Delete Security

The delete API is protected so that a normal user cannot delete another user's profile.

The application verifies the administrator session before allowing the operation.

Conceptually:

```python
if not current_user.is_admin:
    return "Unauthorized"

delete_profile(profile_id)
```

Therefore:

```text
Normal User
     |
     X
Cannot Delete Other Profiles


Admin
     |
     v
Can Delete Profiles
```

This provides basic role-based access control.

---

## 13. PostgreSQL Database

Amazon RDS PostgreSQL stores application data.

Typical profile information stored in PostgreSQL includes:

```text
id
name
email
phone
designation
company
linkedin_url
photo_key
qr_key
status
created_at
updated_at
```

Example:

```text
id:          15
name:        Saransh Rai
email:       saransh@example.com
designation: DevOps Engineer
linkedin:    linkedin.com/in/example
photo_key:   photos/15.jpg
qr_key:      qr/15.png
status:      approved
```

The actual photograph and QR image are not stored directly inside PostgreSQL.

Only their S3 object keys are stored.

---

## 14. Amazon S3 Storage

Amazon S3 is used to persist files.

The bucket maintains folders logically as:

```text
uksf-qr-dev-<AWS-ACCOUNT-ID>

├── photos/
│      ├── 1.jpg
│      ├── 2.jpg
│      └── 15.jpg
│
└── qr/
       ├── 1.png
       ├── 2.png
       └── 15.png
```

This solves an important problem with storing files directly inside the Docker container.

Container storage is temporary because when the container is recreated during deployment, locally stored files can be lost.

Using S3 makes the profile photographs and QR codes persistent.

---

## 15. Profile Photo Flow

When a user uploads a photograph:

```text
User
  |
  v
Upload Photo
  |
  v
Application
  |
  v
Amazon S3

photos/<profile-id>.jpg
```

The database stores only:

```text
photo_key = photos/15.jpg
```

The application can generate a secure S3 URL whenever the photograph needs to be displayed.

---

## 16. QR Code Generation

After the user profile is created and approved, the application creates a unique public profile URL.

Example:

```text
http://<ALB-DNS>/profile/15
```

The application generates a QR code containing this URL.

The generated image is uploaded to:

```text
s3://<bucket-name>/qr/15.png
```

The database can store:

```text
qr_key = qr/15.png
```

---

## 17. QR Scanning Flow

The final QR workflow is:

```text
User Profile
     |
     v
Unique Profile ID
     |
     v
/profile/15
     |
     v
Generate QR
     |
     v
Upload QR to S3
     |
     v
User Downloads / Shares QR
     |
     v
Another Person Scans QR
     |
     v
ALB
     |
     v
EC2 Application
     |
     v
/profile/15
     |
     v
Saransh Rai Profile
```

Therefore, the QR code is directly linked with the respective user's web profile.

---

## 18. Application Load Balancer

Users do not directly access the EC2 instance.

The application is accessed using the AWS Application Load Balancer.

Example:

```text
http://uksf-qr-dev-alb-xxxx.ap-south-1.elb.amazonaws.com
```

The ALB forwards requests to:

```text
EC2:8000
```

The target group performs a health check using:

```text
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

---

## 19. Security Groups

Three different security groups are used.

### ALB Security Group

Allows:

```text
Internet → ALB :80
```

### Application Security Group

Allows:

```text
ALB → EC2 :8000
Admin IP → EC2 :22
```

The EC2 application's port `8000` does not need to be open directly to the internet.

### Database Security Group

Allows:

```text
EC2 → PostgreSQL :5432
```

The PostgreSQL database is therefore isolated from direct public access.

---

## 20. IAM Implementation

The EC2 instance uses an IAM role rather than storing AWS credentials inside the application.

The IAM role provides permission to:

```text
Pull Docker images from ECR

Read objects from S3

Upload objects to S3

Delete required profile objects from S3
```

This avoids keeping AWS access keys inside the application container.

---

## 21. Why Amazon ECR is Used

Amazon ECR is used as the Docker container registry.

Jenkins builds the application:

```bash
docker build
```

and pushes the image to ECR.

Example:

```text
123456789012.dkr.ecr.ap-south-1.amazonaws.com/uksf-qr-dev:25
```

The EC2 instance then pulls this image and runs the application.

This creates a repeatable application deployment process.

---

## 22. Environment Variables

Application configuration is passed using environment variables.

Examples:

```text
AWS_REGION
S3_BUCKET
APP_BASE_URL
DATABASE_URL
```

Example:

```text
AWS_REGION=ap-south-1

S3_BUCKET=uksf-qr-dev-123456789012

APP_BASE_URL=http://<ALB-DNS>

DATABASE_URL=postgresql://qradmin:****@<RDS-ENDPOINT>:5432/uksf_dev
```

Sensitive values such as the PostgreSQL password are stored in Jenkins Credentials rather than hard-coded in the Jenkinsfile.

---

## 23. Complete Application Flow

```text
                         USER
                           |
                           v
                  Create / Edit Profile
                           |
                           v
                     PostgreSQL
                           |
                Upload Profile Photo
                           |
                           v
                         S3
                           |
                           v
                     Admin Review
                           |
                           v
                        Approve
                           |
                           v
                  Generate Profile URL
                           |
                           v
                    Generate QR Code
                           |
                           v
                         S3
                           |
                           v
                     Share QR Code
                           |
                           v
                       QR Scan
                           |
                           v
                          ALB
                           |
                           v
                         EC2
                           |
                           v
                  Public Profile Page
```

For administration:

```text
Admin Login
     |
     v
Admin Dashboard
     |
     +-------- Approve
     |
     +-------- Edit
     |
     +-------- View
     |
     +-------- Delete
```

---

## 24. Key Features Implemented in the POC

The Dev POC demonstrates the following functionality:

```text
User profile creation

User profile editing

Optional profile information

Profile photograph upload

Persistent photograph storage using S3

Unique profile page

QR generation for individual users

Persistent QR storage using S3

QR scan redirects to profile

Admin authentication

Admin approval of profiles

Admin profile management

Admin delete functionality

PostgreSQL persistent database

Dockerized application

Amazon ECR image storage

Terraform infrastructure provisioning

Local Jenkins CI/CD deployment

Application Load Balancer access

Private PostgreSQL networking
```

---

## 25. Benefits of the Architecture

The architecture separates application code, database data and uploaded files.

PostgreSQL is used for structured profile information, while S3 stores photographs and QR images. This prevents uploaded files from being lost when Docker containers are replaced.

Terraform makes the AWS infrastructure repeatable, while Jenkins provides automated application deployment.

The Admin Panel provides centralized control over member profiles through approval, editing and deletion functionality.

---

## 26. Future Enhancements

The current implementation is suitable for a Dev POC. It can later be enhanced with:

* HTTPS using ACM
* Custom domain using Route 53
* S3 lifecycle policies
* CloudWatch monitoring
* Automated database backups
* Soft-delete functionality instead of permanent deletion
* Email verification
* Password reset functionality
* Separate QA and Production environments
* Auto Scaling for production workloads
* CloudFront for static content
* Secrets Manager for database credentials

---

## 27. Conclusion

The UKSF QR Profile POC demonstrates a complete cloud-based member profile management system.

The solution integrates **Terraform, AWS EC2, ALB, RDS PostgreSQL, S3, ECR, Docker, GitHub and Jenkins** to provide automated deployment and persistent application storage.

Users can create and maintain their own profiles, while administrators retain control through profile approval, management and deletion. Each approved member receives a unique QR code that directly opens their public web profile.
