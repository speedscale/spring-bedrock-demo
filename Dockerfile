FROM --platform=$BUILDPLATFORM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /build
COPY .mvn .mvn
COPY mvnw pom.xml ./
RUN ./mvnw -B -ntp dependency:go-offline
COPY src src
RUN ./mvnw -B -ntp -DskipTests package

FROM eclipse-temurin:21-jre-jammy
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=build --chown=10001:10001 /build/target/app.jar app.jar
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/app.jar"]
