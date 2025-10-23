package org.example.utils;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.ThreadPoolExecutor;

@Slf4j
@Configuration
@EnableAsync
public class ThreadPoolTaskConfig {
    @Value("${thread.pool.corePoolSize}")
    private Integer corePoolSize;
    @Value("${thread.pool.maxPoolSize}")
    private Integer maxPoolSize;
    @Value("${thread.pool.queueCapacity}")
    private Integer queueCapacity;
    @Value("${thread.pool.aliveTime}")
    private Integer aliveTime;
    @Value("${thread.pool.awaitTermination}")
    private Integer awaitTermination;
    /**
     * 线程池
     */
    @Bean(name = "cacheTaskExecutor")
    public ThreadPoolTaskExecutor getLotteryQueryCacheTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        //配置核心线程数
        executor.setCorePoolSize(corePoolSize);
        //配置最大线程数
        executor.setMaxPoolSize(maxPoolSize);
        //配置阻塞队列大小
        executor.setQueueCapacity(queueCapacity);
        //线程空闲时间
        executor.setKeepAliveSeconds(aliveTime);
        //是否等待所有任务执行完成再关闭线程池
        executor.setWaitForTasksToCompleteOnShutdown(true);
        //关机等待时间或等待任务执行的最长时间设置
        executor.setAwaitTerminationSeconds(awaitTermination);
        //线程池中的线程名称的默认前缀
        executor.setThreadNamePrefix("lottery-query-cache-executor-");
        //队列和线程池都满时的处理策略
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.initialize();
        return executor;
    }
}