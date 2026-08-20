pipeline {

    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
    }

    environment {

        AWS_REGION = 'ap-south-1'

        ECR_REPO = 'uksf-qr-dev'

        RDS_IDENTIFIER = 'uksf-qr-dev-postgres'

        ALB_NAME = 'uksf-qr-dev-alb'

        CONTAINER_NAME = 'uksf-qr-dev'
    }

    stages {

        stage('Checkout') {

            steps {

                checkout scm
            }
        }


        stage('Build & Push') {

            steps {

                withCredentials([
                    [
                        $class: 'AmazonWebServicesCredentialsBinding',
                        credentialsId: 'aws-dev'
                    ]
                ]) {

                    sh '''
                        set -e

                        ACCOUNT_ID=$(aws sts get-caller-identity \
                            --query Account \
                            --output text)

                        ECR_URL="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"

                        IMAGE="${ECR_URL}:${BUILD_NUMBER}"

                        aws ecr get-login-password \
                            --region "${AWS_REGION}" \
                        | docker login \
                            --username AWS \
                            --password-stdin \
                            "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

                        docker build \
                            -t "${IMAGE}" \
                            .

                        docker push "${IMAGE}"

                        echo "${IMAGE}" > image.txt
                    '''
                }
            }
        }


        stage('Deploy') {

            steps {

                withCredentials([

                    [
                        $class: 'AmazonWebServicesCredentialsBinding',
                        credentialsId: 'aws-dev'
                    ],

                    string(
                        credentialsId: 'qr-dev-db-password',
                        variable: 'DB_PASSWORD'
                    )

                ]) {

                    sshagent(
                        credentials: [
                            'qr-dev-ec2-key'
                        ]
                    ) {

                        sh '''
                            set -e

                            ACCOUNT_ID=$(aws sts get-caller-identity \
                                --query Account \
                                --output text)


                            EC2_IP=$(aws ec2 describe-instances \
                                --filters \
                                "Name=tag:Name,Values=uksf-qr-dev-app" \
                                "Name=instance-state-name,Values=running" \
                                --query 'Reservations[0].Instances[0].PublicIpAddress' \
                                --output text)


                            DB_HOST=$(aws rds describe-db-instances \
                                --db-instance-identifier "${RDS_IDENTIFIER}" \
                                --query 'DBInstances[0].Endpoint.Address' \
                                --output text)


                            ALB_DNS=$(aws elbv2 describe-load-balancers \
                                --names "${ALB_NAME}" \
                                --query 'LoadBalancers[0].DNSName' \
                                --output text)


                            S3_BUCKET="uksf-qr-dev-${ACCOUNT_ID}"


                            IMAGE=$(cat image.txt)


                            ssh \
                                -o StrictHostKeyChecking=no \
                                ubuntu@"${EC2_IP}" \
                                "AWS_REGION='${AWS_REGION}' \
                                 IMAGE='${IMAGE}' \
                                 DB_HOST='${DB_HOST}' \
                                 DB_PASSWORD='${DB_PASSWORD}' \
                                 S3_BUCKET='${S3_BUCKET}' \
                                 APP_BASE_URL='http://${ALB_DNS}' \
                                 bash -s" <<'REMOTE'

                                set -e


                                ACCOUNT_ID=$(echo "$IMAGE" | cut -d. -f1)


                                aws ecr get-login-password \
                                    --region "$AWS_REGION" \
                                | sudo docker login \
                                    --username AWS \
                                    --password-stdin \
                                    "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"


                                sudo docker pull "$IMAGE"


                                sudo docker rm \
                                    -f uksf-qr-dev \
                                    2>/dev/null || true


                                sudo docker run \
                                    -d \
                                    --name uksf-qr-dev \
                                    --restart unless-stopped \
                                    -p 8000:8000 \
                                    -e AWS_REGION="$AWS_REGION" \
                                    -e S3_BUCKET="$S3_BUCKET" \
                                    -e BASE_URL="$APP_BASE_URL" \
                                    -e DATABASE_URL="postgresql+psycopg://qradmin:${DB_PASSWORD}@${DB_HOST}:5432/uksf_dev" \
                                    "$IMAGE"

REMOTE
                        '''
                    }
                }
            }
        }


        stage('Verify') {

            steps {

                withCredentials([
                    [
                        $class: 'AmazonWebServicesCredentialsBinding',
                        credentialsId: 'aws-dev'
                    ]
                ]) {

                    sh '''
                        ALB_DNS=$(aws elbv2 describe-load-balancers \
                            --names "${ALB_NAME}" \
                            --query 'LoadBalancers[0].DNSName' \
                            --output text)


                        curl -f \
                            "http://${ALB_DNS}/health"


                        echo ""

                        echo "Application:"
                        echo "http://${ALB_DNS}"
                    '''
                }
            }
        }
    }
}
