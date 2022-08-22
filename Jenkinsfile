pipeline {
    agent {
        label 'build.dev.cloud.im'
    }
    environment {
        PACKAGE_TYPE="git"

        SEMANTIC_VERSION=sh(returnStdout: true, script: "git describe --abbrev=0 --tags || echo 'v0.0.0-dev'").trim()

        PROJECT_NAME="microsoft-reports"
        PROJECT_KEY="connectors-microsoft-reports"
        PROJECT_VERSION="${SEMANTIC_VERSION}" + "${SEMANTIC_VERSION == 'v0.0.0-dev' ? '.' : '-'}" + "${BUILD_NUMBER}"
        PROJECT_DELIVERABLE="${PROJECT_NAME}-${PROJECT_VERSION}.${PACKAGE_TYPE}"

        HAS_PYPROJECT_FILE = fileExists 'pyproject.toml'
        HAS_REQUIREMENTS_FILE = fileExists 'requirements.txt'
    }
    stages {
        stage('Environment Setup') {
            steps {
                sh """
                /usr/local/bin/python3.8 -m venv venv
                source venv/bin/activate

                pip install --upgrade pip
                pip install pylint poetry --trusted-host pypi.int.zone
                poetry check
                poetry env info

                if ${HAS_PYPROJECT_FILE}
                then
                    poetry config virtualenvs.create false
                    poetry install
                fi

                if ${HAS_REQUIREMENTS_FILE}
                then
                    pip install -r requirements.txt
                fi
                """
            }
        }
        stage('Test Execution') {
            steps {
                sh """
                source venv/bin/activate
                poetry run pytest -p no:cacheprovider
                """
            }
        }
        stage('SonarQube Analysis') {
            steps {
                script {
                    def SCANNER_HOME = tool name: 'SonarQubeIntZoneScanner', type: 'hudson.plugins.sonar.SonarRunnerInstallation';
                    withSonarQubeEnv('SonarQubeIntZone') {
                        sh """
                        export JAVA_HOME=/usr/lib/jvm/java-11-openjdk
                        ${SCANNER_HOME}/bin/sonar-scanner \
                        -Dsonar.project.tags=connectors \
                        -Dsonar.projectKey=${PROJECT_KEY} \
                        -Dsonar.sources=reports/ \
                        -Dsonar.tests=tests/ \
                        -Dsonar.python.coverage.reportPaths=coverage.xml \
                        -Dsonar.python.pylint=venv/bin/pylint
                        """
                    }
                }
            }
        }
    }
    post {
        always {
            cleanWs()
        }
    }
}